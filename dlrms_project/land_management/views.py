from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

class ParcelListView(LoginRequiredMixin, TemplateView):
    template_name = 'land_management/parcel_list.html'

class ParcelCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'land_management/parcel_create.html'

class ParcelDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'land_management/parcel_detail.html'

class ParcelUpdateView(LoginRequiredMixin, TemplateView):
    template_name = 'land_management/parcel_update.html'

class MapView(LoginRequiredMixin, TemplateView):
    template_name = 'land_management/map.html'