from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.db.models import Q
from django.contrib import messages

from parents.models import ParentProfile, ParentStudent
from parents.forms import ParentProfileCreateForm, ParentStudentLinkForm
from students.models import Student
from core.permissions import AdminOrPrincipalRequiredMixin, SchoolAdminRequiredMixin, ParentRequiredMixin
from core.utils import log_audit
from core.models import AuditLog

class ParentListView(AdminOrPrincipalRequiredMixin, ListView):
    model = ParentProfile
    template_name = 'parents/parent_list.html'
    context_object_name = 'parents'
    paginate_by = 25

    def get_queryset(self):
        qs = ParentProfile.objects.filter(is_deleted=False).prefetch_related('linked_students__student')
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            qs = qs.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(primary_phone__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class ParentDetailView(AdminOrPrincipalRequiredMixin, DetailView):
    model = ParentProfile
    template_name = 'parents/parent_detail.html'
    context_object_name = 'parent'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['linked_students'] = self.object.linked_students.filter(is_deleted=False).select_related('student')
        context['link_form'] = ParentStudentLinkForm()
        return context


class ParentCreateView(SchoolAdminRequiredMixin, CreateView):
    model = ParentProfile
    form_class = ParentProfileCreateForm
    template_name = 'parents/parent_form.html'
    success_url = reverse_lazy('parents:parent_list')

    def form_valid(self, form):
        messages.success(self.request, f"Parent '{form.cleaned_data['first_name']} {form.cleaned_data['last_name']}' registered.")
        response = super().form_valid(form)
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Parents',
            model_name='ParentProfile',
            object_id=str(self.object.id),
            object_repr=self.object.full_name
        )
        return response


class ParentLinkStudentView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk):
        parent = get_object_or_404(ParentProfile, pk=pk)
        student_id = request.POST.get('student')
        relationship_type = request.POST.get('relationship_type', ParentStudent.RelationshipType.FATHER)
        is_primary_contact = request.POST.get('is_primary_contact') in ['on', 'true', '1', True]
        can_pickup_child = request.POST.get('can_pickup_child') in ['on', 'true', '1', True]

        if not student_id:
            messages.error(request, "Please select a valid student to link.")
            return redirect('parents:parent_detail', pk=parent.pk)

        student = get_object_or_404(Student, pk=student_id)

        link, created = ParentStudent.objects.update_or_create(
            parent=parent,
            student=student,
            defaults={
                'relationship_type': relationship_type,
                'is_primary_contact': is_primary_contact,
                'can_pickup_child': can_pickup_child,
                'is_deleted': False
            }
        )

        # Also update emergency contact on student record if designated primary
        if is_primary_contact and not student.emergency_contact_phone:
            student.emergency_contact_name = parent.full_name
            student.emergency_contact_phone = parent.primary_phone
            student.emergency_contact_relation = link.get_relationship_type_display()
            student.save()

        if created:
            messages.success(request, f"Student '{student.full_name}' ({student.admission_number}) successfully linked to {parent.full_name}.")
        else:
            messages.success(request, f"Relationship link for student '{student.full_name}' successfully updated.")

        log_audit(
            request,
            action=AuditLog.Action.UPDATE if not created else AuditLog.Action.CREATE,
            module='Parents',
            model_name='ParentStudent',
            object_id=str(link.id),
            object_repr=f"{parent.full_name} -> {student.full_name}"
        )
        return redirect('parents:parent_detail', pk=parent.pk)


class ParentUnlinkStudentView(SchoolAdminRequiredMixin, View):
    def post(self, request, pk, student_id):
        parent = get_object_or_404(ParentProfile, pk=pk)
        student = get_object_or_404(Student, pk=student_id)

        links = ParentStudent.objects.filter(parent=parent, student=student)
        if links.exists():
            links.delete()
            messages.success(request, f"Student '{student.full_name}' unlinked from {parent.full_name}.")
            log_audit(
                request,
                action=AuditLog.Action.DELETE,
                module='Parents',
                model_name='ParentStudent',
                object_id=str(student.id),
                object_repr=f"Unlinked {student.full_name} from {parent.full_name}"
            )
        else:
            messages.warning(request, "Student was not linked to this parent.")
        return redirect('parents:parent_detail', pk=parent.pk)


class ParentPortalView(ParentRequiredMixin, TemplateView):
    """
    Dedicated Parent Portal view supporting instant switching between multiple children.
    """
    template_name = 'dashboards/parent_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parent_profile = getattr(self.request.user, 'parent_profile', None)
        
        children = []
        active_child = None

        if parent_profile:
            links = parent_profile.linked_students.filter(is_deleted=False).select_related('student')
            children = [link.student for link in links]

            # Session active child selection
            active_child_id = self.request.session.get('active_child_id')
            if active_child_id:
                active_child = next((c for c in children if str(c.id) == str(active_child_id)), None)
            
            if not active_child and children:
                active_child = children[0]
                self.request.session['active_child_id'] = str(active_child.id)

        context['parent_profile'] = parent_profile
        context['children'] = children
        context['active_child'] = active_child
        return context


class ParentSwitchChildView(ParentRequiredMixin, View):
    def post(self, request, child_id):
        parent_profile = getattr(request.user, 'parent_profile', None)
        if parent_profile:
            # Verify child is actually linked to this parent (Object-Level Authorization Check)
            is_linked = parent_profile.linked_students.filter(student_id=child_id, is_deleted=False).exists()
            if is_linked:
                request.session['active_child_id'] = str(child_id)
                child = Student.objects.filter(pk=child_id).first()
                messages.success(request, f"Switched view to {child.full_name if child else 'child'}.")
            else:
                messages.error(request, "Unauthorized child selection.")
        return redirect('accounts:parent_dashboard')
