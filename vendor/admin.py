from django.contrib import admin
from .models import Vendor,PurchaseOrder,HistoricalPerformance

admin.register(Vendor)
admin.register(PurchaseOrder)
admin.register(HistoricalPerformance)
