from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

class ApplicationListView(LoginRequiredMixin, TemplateView):
    template_name = 'applications/application_list.html'

class ApplicationCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'applications/application_create.html'

class ApplicationDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'applications/application_detail.html'

class ApplicationUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'applications/application_update.html'

class ApplicationReviewView(LoginRequiredMixin, TemplateView):
    template_name = 'applications/application_review.html'