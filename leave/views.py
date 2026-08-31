from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, CreateView, DetailView
from django.contrib import messages
from django.utils import timezone

from leave.models import LeaveType, LeaveRequest
from leave.forms import LeaveRequestForm, LeaveReviewForm
from core.permissions import RoleRequiredMixin, AdminOrPrincipalRequiredMixin
from core.utils import log_audit
from core.models import AuditLog

class LeaveRequestListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'ACCOUNTANT', 'LIBRARIAN', 'SUPPORT_STAFF', 'STUDENT']
    model = LeaveRequest
    template_name = 'leave/leave_list.html'
    context_object_name = 'leave_requests'
    paginate_by = 25

    def get_queryset(self):
        qs = LeaveRequest.objects.filter(is_deleted=False).select_related('user', 'leave_type', 'reviewed_by')
        # If regular staff/student, only show own requests
        if not (self.request.user.is_superadmin or self.request.user.is_school_admin or self.request.user.is_principal):
            qs = qs.filter(user=self.request.user)
            
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_leaves = LeaveRequest.objects.filter(is_deleted=False)
        context['pending_count'] = all_leaves.filter(status=LeaveRequest.Status.PENDING).count()
        context['approved_count'] = all_leaves.filter(status=LeaveRequest.Status.APPROVED).count()
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class LeaveRequestCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'ACCOUNTANT', 'LIBRARIAN', 'SUPPORT_STAFF', 'STUDENT']
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'leave/leave_form.html'
    success_url = reverse_lazy('leave:list')

    def form_valid(self, form):
        req = form.save(commit=False)
        req.user = self.request.user
        req.save()
        messages.success(self.request, "Leave request submitted for review.")
        return redirect('leave:list')


class LeaveReviewActionView(AdminOrPrincipalRequiredMixin, View):
    """
    Approve or Reject leave request.
    """
    def post(self, request, pk):
        leave_req = get_object_or_404(LeaveRequest, pk=pk)
        action = request.POST.get('action') # 'APPROVE' or 'REJECT'
        remarks = request.POST.get('review_remarks', '')

        if action == 'APPROVE':
            leave_req.status = LeaveRequest.Status.APPROVED
            messages.success(request, f"Leave request for {leave_req.user.email} approved.")
        elif action == 'REJECT':
            leave_req.status = LeaveRequest.Status.REJECTED
            messages.warning(request, f"Leave request for {leave_req.user.email} rejected.")

        leave_req.reviewed_by = request.user
        leave_req.review_remarks = remarks
        leave_req.save()

        log_audit(
            request,
            action=AuditLog.Action.UPDATE,
            module='Leave',
            model_name='LeaveRequest',
            object_id=str(leave_req.id),
            object_repr=f"Leave {leave_req.status} for {leave_req.user.email}"
        )
        return redirect('leave:list')
