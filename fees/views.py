import uuid
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.db import transaction, models
from django.db.models import Q, Sum, F, Count
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

from fees.models import (
    FeeCategory, FeeStructure, StudentFeeInvoice, StudentFeePayment,
    FeeConcession, StudentConcession, FeeFineRule, InvoiceLineItem
)
from fees.forms import (
    FeeCategoryForm, FeeStructureForm, StudentFeeInvoiceForm,
    StudentFeePaymentForm, InvoiceBatchGenerationForm,
    FeeConcessionForm, StudentConcessionAssignForm, FeeFineRuleForm
)
from academics.models import AcademicYear, ClassLevel, Section
from students.models import Student, StudentEnrollment
from core.permissions import AccountantRequiredMixin, RoleRequiredMixin
from core.utils import log_audit, export_to_csv, export_to_excel
from core.models import AuditLog, SchoolSetting

class FeeOverviewDashboardView(AccountantRequiredMixin, TemplateView):
    """
    Finance & Fee Management Overview with collections and receivables metrics in INR (₹).
    """
    template_name = 'fees/fee_overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()

        invoices = StudentFeeInvoice.objects.filter(is_deleted=False)
        if academic_year:
            invoices = invoices.filter(academic_year=academic_year)

        # Trigger auto-fine recalculation for overdue invoices
        for inv in invoices.filter(status__in=[StudentFeeInvoice.Status.UNPAID, StudentFeeInvoice.Status.PARTIAL, StudentFeeInvoice.Status.OVERDUE])[:50]:
            inv.calculate_and_apply_fine()

        total_billed = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        total_collected = invoices.aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')
        total_outstanding = invoices.aggregate(Sum('balance_amount'))['balance_amount__sum'] or Decimal('0.00')
        total_fines = invoices.aggregate(Sum('fine_amount'))['fine_amount__sum'] or Decimal('0.00')
        total_discounts = invoices.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0.00')
        
        unpaid_count = invoices.filter(status=StudentFeeInvoice.Status.UNPAID).count()
        paid_count = invoices.filter(status=StudentFeeInvoice.Status.PAID).count()
        partial_count = invoices.filter(status=StudentFeeInvoice.Status.PARTIAL).count()
        overdue_count = invoices.filter(status=StudentFeeInvoice.Status.OVERDUE).count()

        recent_payments = StudentFeePayment.objects.filter(is_deleted=False).select_related(
            'invoice__student_enrollment__student', 'invoice__student_enrollment__section'
        ).order_by('-created_at')[:10]

        context['academic_year'] = academic_year
        context['total_billed'] = total_billed
        context['total_collected'] = total_collected
        context['total_outstanding'] = total_outstanding
        context['total_fines'] = total_fines
        context['total_discounts'] = total_discounts
        context['unpaid_count'] = unpaid_count
        context['paid_count'] = paid_count
        context['partial_count'] = partial_count
        context['overdue_count'] = overdue_count
        context['recent_payments'] = recent_payments
        return context


class FeePOSCounterView(AccountantRequiredMixin, TemplateView):
    """
    Rapid Point-of-Sale (POS) Fee Counter collection interface.
    Allows searching students by Name, Admission No, Roll No, or Phone, displaying live pending dues,
    and recording multi-mode payments (Cash, UPI with UTR, Cheque/DD, Card) with instant 3-part receipt generation.
    """
    template_name = 'fees/fee_pos_counter.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        selected_student_id = self.request.GET.get('student_id')
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()

        search_results = []
        selected_student = None
        current_enrollment = None
        pending_invoices = []
        active_concessions = []
        total_due = Decimal('0.00')

        if query:
            search_results = Student.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(admission_number__icontains=query) |
                Q(emergency_contact_phone__icontains=query) |
                Q(enrollments__roll_number__icontains=query)
            ).filter(is_deleted=False).distinct()[:15]

        if selected_student_id:
            selected_student = Student.objects.filter(pk=selected_student_id, is_deleted=False).first()
            if selected_student:
                current_enrollment = selected_student.current_enrollment
                if current_enrollment:
                    active_concessions = StudentConcession.objects.filter(
                        student_enrollment=current_enrollment,
                        is_active=True
                    ).select_related('concession')

                    invoices_qs = StudentFeeInvoice.objects.filter(
                        student_enrollment=current_enrollment,
                        is_deleted=False
                    ).exclude(status=StudentFeeInvoice.Status.PAID).order_by('due_date')

                    for inv in invoices_qs:
                        inv.calculate_and_apply_fine()
                        pending_invoices.append(inv)
                        total_due += inv.balance_amount

        context['query'] = query
        context['search_results'] = search_results
        context['selected_student'] = selected_student
        context['current_enrollment'] = current_enrollment
        context['pending_invoices'] = pending_invoices
        context['active_concessions'] = active_concessions
        context['total_due'] = total_due
        context['today'] = timezone.now().date()
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        invoice_id = request.POST.get('invoice_id')
        amount_paid_str = request.POST.get('amount_paid', '0').strip()
        payment_method = request.POST.get('payment_method', StudentFeePayment.PaymentMethod.CASH)
        upi_utr_number = request.POST.get('upi_utr_number', '').strip()
        cheque_number = request.POST.get('cheque_number', '').strip()
        cheque_bank_name = request.POST.get('cheque_bank_name', '').strip()
        cheque_date = request.POST.get('cheque_date') or None
        notes = request.POST.get('notes', '').strip()

        invoice = get_object_or_404(StudentFeeInvoice, pk=invoice_id)
        try:
            amount_paid = Decimal(amount_paid_str)
        except Exception:
            amount_paid = Decimal('0.00')

        if amount_paid <= 0:
            messages.error(request, "Please enter a valid payment amount greater than ₹0.")
            return redirect(f"{reverse('fees:pos_counter')}?student_id={invoice.student_enrollment.student.id}")

        if amount_paid > invoice.balance_amount:
            amount_paid = invoice.balance_amount

        receipt_no = f"REC-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

        payment = StudentFeePayment.objects.create(
            invoice=invoice,
            receipt_number=receipt_no,
            payment_date=timezone.now().date(),
            amount_paid=amount_paid,
            payment_method=payment_method,
            upi_utr_number=upi_utr_number,
            cheque_number=cheque_number,
            cheque_bank_name=cheque_bank_name,
            cheque_date=cheque_date,
            transaction_id=upi_utr_number or cheque_number or f"POS-{uuid.uuid4().hex[:6].upper()}",
            notes=notes,
            collected_by=request.user
        )

        messages.success(request, f"Fee payment of ₹{payment.amount_paid} collected successfully. (Receipt #{payment.receipt_number})")
        log_audit(
            request,
            action=AuditLog.Action.CREATE,
            module='Fees',
            model_name='StudentFeePayment',
            object_id=str(payment.id),
            object_repr=f"POS Collection: {payment.receipt_number} - ₹{payment.amount_paid}"
        )
        return redirect('fees:receipt_print', pk=payment.pk)


class FeeReceiptPrintView(RoleRequiredMixin, DetailView):
    """
    Official 3-Part Institutional Fee Receipt (Student Copy, School Copy, Bank/Accounts Copy).
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'ACCOUNTANT', 'PARENT', 'STUDENT']
    model = StudentFeePayment
    template_name = 'fees/receipt_print.html'
    context_object_name = 'payment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.object.invoice
        student = invoice.student_enrollment.student
        enrollment = invoice.student_enrollment
        school_setting = SchoolSetting.objects.first()

        context['invoice'] = invoice
        context['student'] = student
        context['enrollment'] = enrollment
        context['school_setting'] = school_setting
        return context


class FeeReceiptPDFDownloadView(RoleRequiredMixin, View):
    """
    Generates and streams official server-side vector PDF fee payment receipt.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'ACCOUNTANT', 'PARENT', 'STUDENT']

    def get(self, request, pk, *args, **kwargs):
        payment = get_object_or_404(StudentFeePayment, pk=pk, is_deleted=False)
        from core.pdf_generator import generate_fee_receipt_pdf
        from django.http import HttpResponse
        
        pdf_buffer = generate_fee_receipt_pdf(payment)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Receipt_{payment.receipt_number}.pdf"'
        return response


class FeeDefaultersListView(AccountantRequiredMixin, TemplateView):
    """
    Aging fee dues and defaulters register.
    """
    template_name = 'fees/fee_defaulters_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        class_id = self.request.GET.get('class_level')
        days_bracket = self.request.GET.get('bracket', 'ALL')

        invoices_qs = StudentFeeInvoice.objects.filter(
            is_deleted=False
        ).exclude(status=StudentFeeInvoice.Status.PAID).select_related(
            'student_enrollment__student', 'student_enrollment__section__class_level'
        )

        if academic_year:
            invoices_qs = invoices_qs.filter(academic_year=academic_year)
        if class_id:
            invoices_qs = invoices_qs.filter(student_enrollment__section__class_level_id=class_id)

        # Apply aging filters
        today = timezone.now().date()
        defaulters = []
        total_defaulter_amount = Decimal('0.00')

        for inv in invoices_qs:
            inv.calculate_and_apply_fine()
            days_overdue = (today - inv.due_date).days if inv.due_date and inv.due_date < today else 0

            if days_bracket == '30_PLUS' and days_overdue < 30:
                continue
            if days_bracket == '60_PLUS' and days_overdue < 60:
                continue
            if days_bracket == '90_PLUS' and days_overdue < 90:
                continue

            total_defaulter_amount += inv.balance_amount
            defaulters.append({
                'invoice': inv,
                'student': inv.student_enrollment.student,
                'enrollment': inv.student_enrollment,
                'days_overdue': days_overdue,
                'balance': inv.balance_amount
            })

        context['classes'] = ClassLevel.objects.filter(is_deleted=False)
        context['selected_class'] = class_id
        context['selected_bracket'] = days_bracket
        context['defaulters'] = defaulters
        context['total_defaulter_amount'] = total_defaulter_amount
        context['defaulters_count'] = len(defaulters)
        return context


class FeeConcessionListView(AccountantRequiredMixin, ListView):
    """
    Manage institutional fee concession schemes and student assignments.
    """
    model = FeeConcession
    template_name = 'fees/concession_list.html'
    context_object_name = 'concessions'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        context['student_concessions'] = StudentConcession.objects.filter(
            academic_year=academic_year, is_deleted=False
        ).select_related('student_enrollment__student', 'student_enrollment__section', 'concession') if academic_year else []
        context['concession_form'] = FeeConcessionForm()
        context['assign_form'] = StudentConcessionAssignForm(initial={'academic_year': academic_year})
        return context


class FeeConcessionCreateView(AccountantRequiredMixin, CreateView):
    model = FeeConcession
    form_class = FeeConcessionForm
    template_name = 'fees/concession_form.html'
    success_url = reverse_lazy('fees:concession_list')

    def form_valid(self, form):
        messages.success(self.request, f"Concession scheme '{form.cleaned_data['name']}' created.")
        return super().form_valid(form)


class StudentConcessionAssignView(AccountantRequiredMixin, View):
    def post(self, request):
        form = StudentConcessionAssignForm(request.POST)
        if form.is_valid():
            assign = form.save(commit=False)
            assign.approved_by = request.user
            assign.save()
            messages.success(request, f"Concession '{assign.concession.name}' assigned to {assign.student_enrollment.student.full_name}.")
        else:
            messages.error(request, "Failed to assign concession. Please check inputs.")
        return redirect('fees:concession_list')


class FeeStructureListView(AccountantRequiredMixin, ListView):
    model = FeeStructure
    template_name = 'fees/fee_structure_list.html'
    context_object_name = 'structures'

    def get_queryset(self):
        year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        return FeeStructure.objects.filter(academic_year=year).select_related('class_level', 'fee_category') if year else FeeStructure.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        academic_year = getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        classes = ClassLevel.objects.filter(is_deleted=False)
        categories = FeeCategory.objects.all()

        # Build Class x Category Matrix
        matrix = []
        structures = FeeStructure.objects.filter(academic_year=academic_year)
        struct_map = {(s.class_level_id, s.fee_category_id): s for s in structures}

        for cl in classes:
            row_items = []
            total_class_fee = Decimal('0.00')
            for cat in categories:
                st = struct_map.get((cl.id, cat.id))
                amount = st.amount if st else Decimal('0.00')
                total_class_fee += amount
                row_items.append({'category': cat, 'amount': amount, 'structure': st})
            matrix.append({'class_level': cl, 'items': row_items, 'total': total_class_fee})

        context['categories'] = categories
        context['matrix'] = matrix
        context['classes'] = classes
        context['fine_rules'] = FeeFineRule.objects.filter(academic_year=academic_year)
        context['fine_form'] = FeeFineRuleForm(initial={'academic_year': academic_year})
        return context



class FeeStructureUpdateView(AccountantRequiredMixin, UpdateView):
    model = FeeStructure
    form_class = FeeStructureForm
    template_name = 'fees/fee_structure_form.html'
    success_url = reverse_lazy('fees:structure_list')

    def form_valid(self, form):
        messages.success(self.request, f"Fee structure for '{self.object.class_level.name}' updated successfully.")
        return super().form_valid(form)


class FeeStructureDeleteView(AccountantRequiredMixin, DeleteView):
    model = FeeStructure
    template_name = 'fees/fee_structure_confirm_delete.html'
    success_url = reverse_lazy('fees:structure_list')

    def form_valid(self, form):
        st = self.get_object()
        name = f"{st.class_level.name} - {st.fee_category.name}"
        st.delete()
        messages.warning(self.request, f"Fee rule '{name}' removed.")
        return redirect(self.success_url)

class FeeStructureCreateView(AccountantRequiredMixin, CreateView):
    model = FeeStructure
    form_class = FeeStructureForm
    template_name = 'fees/fee_structure_form.html'
    success_url = reverse_lazy('fees:structure_list')

    def form_valid(self, form):
        messages.success(self.request, "Fee structure rule created successfully.")
        return super().form_valid(form)


class FeeFineRuleCreateView(AccountantRequiredMixin, CreateView):
    model = FeeFineRule
    form_class = FeeFineRuleForm
    template_name = 'fees/fee_structure_form.html'
    success_url = reverse_lazy('fees:structure_list')

    def form_valid(self, form):
        messages.success(self.request, f"Late fee fine rule '{form.cleaned_data['name']}' saved.")
        return super().form_valid(form)


class StudentFeeInvoiceListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'ACCOUNTANT', 'PARENT', 'STUDENT']
    model = StudentFeeInvoice
    template_name = 'fees/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 25

    def get_queryset(self):
        qs = StudentFeeInvoice.objects.filter(is_deleted=False).select_related(
            'student_enrollment__student', 'student_enrollment__section__class_level'
        )

        if self.request.user.is_student:
            student = getattr(self.request.user, 'student_profile', None)
            if student and student.current_enrollment:
                qs = qs.filter(student_enrollment=student.current_enrollment)
        elif self.request.user.is_parent:
            parent = getattr(self.request.user, 'parent_profile', None)
            if parent:
                linked_students = parent.children
                qs = qs.filter(student_enrollment__student__in=linked_students)

        search = self.request.GET.get('search', '').strip()
        status = self.request.GET.get('status', '')
        if search:
            qs = qs.filter(
                Q(invoice_number__icontains=search) |
                Q(student_enrollment__student__first_name__icontains=search) |
                Q(student_enrollment__student__last_name__icontains=search) |
                Q(student_enrollment__student__admission_number__icontains=search)
            )
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class StudentFeeInvoiceDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'ACCOUNTANT', 'PARENT', 'STUDENT']
    model = StudentFeeInvoice
    template_name = 'fees/invoice_detail.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object.calculate_and_apply_fine()
        context['payments'] = self.object.payments.filter(is_deleted=False).order_by('-payment_date')
        context['line_items'] = self.object.line_items.filter(is_deleted=False)
        context['payment_form'] = StudentFeePaymentForm(initial={'amount_paid': self.object.balance_amount})
        return context


class FeePaymentCreateView(AccountantRequiredMixin, View):
    """
    Collect fee payment and record receipt.
    """
    @transaction.atomic
    def post(self, request, pk):
        invoice = get_object_or_404(StudentFeeInvoice, pk=pk)
        form = StudentFeePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.receipt_number = f"REC-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
            payment.collected_by = request.user
            payment.save()

            messages.success(request, f"Payment of ₹{payment.amount_paid} recorded (Receipt: {payment.receipt_number}).")
            log_audit(
                request,
                action=AuditLog.Action.CREATE,
                module='Fees',
                model_name='StudentFeePayment',
                object_id=str(payment.id),
                object_repr=f"{payment.receipt_number} - ₹{payment.amount_paid}"
            )
            return redirect('fees:receipt_print', pk=payment.pk)
        else:
            messages.error(request, "Failed to record payment. Please check inputs.")
        return redirect('fees:invoice_detail', pk=invoice.pk)


class InvoiceBatchGenerationView(AccountantRequiredMixin, TemplateView):
    """
    Batch invoice generation for an entire class or section with automatic concession deductions.
    """
    template_name = 'fees/invoice_batch_generate.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = InvoiceBatchGenerationForm(initial={
            'academic_year': getattr(self.request, 'academic_year', None) or AcademicYear.objects.filter(is_current=True).first()
        })
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = InvoiceBatchGenerationForm(request.POST)
        if form.is_valid():
            year = form.cleaned_data['academic_year']
            class_level = form.cleaned_data['class_level']
            section = form.cleaned_data['section']
            fee_category = form.cleaned_data['fee_category']
            title = form.cleaned_data['title']
            amount = form.cleaned_data['amount']
            due_date = form.cleaned_data['due_date']

            enrollments_qs = StudentEnrollment.objects.filter(
                academic_year=year,
                section__class_level=class_level,
                is_current=True,
                is_deleted=False
            )
            if section:
                enrollments_qs = enrollments_qs.filter(section=section)

            created_count = 0
            for enroll in enrollments_qs:
                invoice_no = f"INV-{year.name[:4]}-{uuid.uuid4().hex[:8].upper()}"
                
                # Check for active student concessions
                concession_obj = None
                discount = Decimal('0.00')
                active_conc = StudentConcession.objects.filter(
                    student_enrollment=enroll,
                    academic_year=year,
                    is_active=True
                ).select_related('concession').first()

                if active_conc:
                    concession_obj = active_conc.concession
                    if concession_obj.concession_type == FeeConcession.ConcessionType.PERCENTAGE:
                        discount = round((amount * concession_obj.discount_value) / Decimal('100.00'), 2)
                    else:
                        discount = min(concession_obj.discount_value, amount)

                net_initial = max(Decimal('0.00'), amount - discount)

                inv = StudentFeeInvoice.objects.create(
                    invoice_number=invoice_no,
                    student_enrollment=enroll,
                    academic_year=year,
                    title=title,
                    issue_date=timezone.now().date(),
                    due_date=due_date,
                    total_amount=amount,
                    discount_amount=discount,
                    concession_applied=concession_obj,
                    fine_amount=Decimal('0.00'),
                    paid_amount=Decimal('0.00'),
                    balance_amount=net_initial,
                    status=StudentFeeInvoice.Status.UNPAID
                )

                # Create itemized line item
                InvoiceLineItem.objects.create(
                    invoice=inv,
                    fee_category=fee_category,
                    title=title,
                    amount=amount
                )
                created_count += 1

            messages.success(request, f"Successfully generated {created_count} fee invoices for {class_level.name}.")
            return redirect('fees:invoice_list')

        return render(request, self.template_name, {'form': form})


class ParentOnlineFeePaymentView(RoleRequiredMixin, View):
    """
    Simulated online payment checkout portal for Parents & Students.
    """
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'ACCOUNTANT', 'PARENT', 'STUDENT']

    @transaction.atomic
    def post(self, request, pk):
        invoice = get_object_or_404(StudentFeeInvoice, pk=pk)
        pay_amount = invoice.balance_amount
        gateway_mode = request.POST.get('gateway_mode', 'UPI_INSTANT')
        upi_id = request.POST.get('upi_id', 'parent@okhdfcbank')

        if pay_amount <= 0:
            messages.info(request, "This invoice is already fully cleared.")
            return redirect('fees:invoice_detail', pk=invoice.pk)

        receipt_no = f"PAY-{timezone.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
        payment = StudentFeePayment.objects.create(
            invoice=invoice,
            receipt_number=receipt_no,
            payment_date=timezone.now().date(),
            amount_paid=pay_amount,
            payment_method=StudentFeePayment.PaymentMethod.ONLINE,
            transaction_id=f"GATEWAY-{uuid.uuid4().hex[:10].upper()}",
            upi_utr_number=f"UTR{uuid.uuid4().hex[:8].upper()}",
            notes=f"Instant Parent Portal Payment via {gateway_mode} ({upi_id})",
            collected_by=request.user
        )

        messages.success(request, f"Online payment of ₹{payment.amount_paid} received! Receipt #{payment.receipt_number} generated.")
        return redirect('fees:receipt_print', pk=payment.pk)

