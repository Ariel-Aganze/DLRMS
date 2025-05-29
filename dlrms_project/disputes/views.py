from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin

class DisputeListView(LoginRequiredMixin, TemplateView):
    template_name = 'disputes/dispute_list.html'

class DisputeCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'disputes/dispute_create.html'

class DisputeDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'disputes/dispute_detail.html'

class DisputeResolveView(LoginRequiredMixin, TemplateView):
    template_name = 'disputes/dispute_resolve.html'