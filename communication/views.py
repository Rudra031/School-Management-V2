from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from communication.models import Notice, InAppNotification
from communication.forms import NoticeForm
from core.permissions import RoleRequiredMixin, AdminOrPrincipalRequiredMixin
from core.utils import log_audit
from core.models import AuditLog

class NoticeBoardView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'ACCOUNTANT', 'LIBRARIAN', 'SUPPORT_STAFF', 'STUDENT', 'PARENT']
    model = Notice
    template_name = 'communication/notice_board.html'
    context_object_name = 'notices'
    paginate_by = 20

    def get_queryset(self):
        qs = Notice.objects.filter(is_published=True, is_deleted=False)
        user = self.request.user

        # Filter by Target Audience
        if not (user.is_superadmin or user.is_school_admin or user.is_principal):
            if user.is_teacher:
                qs = qs.filter(target_audience__in=[Notice.Audience.ALL, Notice.Audience.TEACHERS])
            elif user.is_student:
                qs = qs.filter(target_audience__in=[Notice.Audience.ALL, Notice.Audience.STUDENTS])
            elif user.is_parent:
                qs = qs.filter(target_audience__in=[Notice.Audience.ALL, Notice.Audience.PARENTS])
            else:
                qs = qs.filter(target_audience__in=[Notice.Audience.ALL, Notice.Audience.STAFF])

        search = self.request.GET.get('search', '').strip()
        audience = self.request.GET.get('audience', '')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search))
        if audience:
            qs = qs.filter(target_audience=audience)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_audience'] = self.request.GET.get('audience', '')
        context['audiences'] = Notice.Audience.choices
        return context


class NoticeDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'ACCOUNTANT', 'LIBRARIAN', 'SUPPORT_STAFF', 'STUDENT', 'PARENT']
    model = Notice
    template_name = 'communication/notice_detail.html'
    context_object_name = 'notice'


class NoticeCreateView(AdminOrPrincipalRequiredMixin, CreateView):
    model = Notice
    form_class = NoticeForm
    template_name = 'communication/notice_form.html'
    success_url = reverse_lazy('communication:notice_board')

    def form_valid(self, form):
        notice = form.save(commit=False)
        notice.created_by = self.request.user
        notice.save()
        messages.success(self.request, f"Notice '{notice.title}' published successfully.")
        log_audit(
            self.request,
            action=AuditLog.Action.CREATE,
            module='Communication',
            model_name='Notice',
            object_id=str(notice.id),
            object_repr=notice.title
        )
        return redirect('communication:notice_board')


class NotificationListView(RoleRequiredMixin, ListView):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'ACCOUNTANT', 'LIBRARIAN', 'SUPPORT_STAFF', 'STUDENT', 'PARENT']
    model = InAppNotification
    template_name = 'communication/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 30

    def get_queryset(self):
        return InAppNotification.objects.filter(recipient=self.request.user, is_deleted=False)


class NotificationMarkReadView(RoleRequiredMixin, View):
    allowed_roles = ['SUPERADMIN', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'ACCOUNTANT', 'LIBRARIAN', 'SUPPORT_STAFF', 'STUDENT', 'PARENT']

    def post(self, request, pk):
        notif = get_object_or_404(InAppNotification, pk=pk, recipient=request.user)
        notif.is_read = True
        notif.save()
        if notif.link_url:
            return redirect(notif.link_url)
        return redirect('communication:notifications')
