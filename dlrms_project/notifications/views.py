from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin

class NotificationListView(LoginRequiredMixin, TemplateView):
    template_name = 'notifications/notification_list.html'

class MarkNotificationReadView(LoginRequiredMixin, TemplateView):
    template_name = 'notifications/mark_read.html'

class MarkAllReadView(LoginRequiredMixin, TemplateView):
    template_name = 'notifications/mark_all_read.html'