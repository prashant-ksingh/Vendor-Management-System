from django.db.models import Count, Avg
from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from .models import Vendor, PurchaseOrder, HistoricalPerformance
from .serializers import VendorSerializer, PurchaseOrderSerializer, HistoricalPerformanceSerializer

class VendorListCreateView(generics.ListCreateAPIView):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer

class VendorDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer

class PurchaseOrderListCreateView(generics.ListCreateAPIView):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer

    def perform_create(self, serializer):
        # Update vendor performance metrics upon PO creation
        instance = serializer.save()
        self.update_vendor_performance(instance.vendor)

class PurchaseOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer

    def perform_update(self, serializer):
        # Update vendor performance metrics upon PO update
        instance = serializer.save()
        self.update_vendor_performance(instance.vendor)

    def perform_destroy(self, instance):
        # Update vendor performance metrics upon PO deletion
        self.update_vendor_performance(instance.vendor)
        instance.delete()

    def update_vendor_performance(self, vendor):
        # On-Time Delivery Rate
        completed_pos = PurchaseOrder.objects.filter(vendor=vendor, status='completed')
        on_time_delivered_pos = completed_pos.filter(delivery_date__lte=timezone.now())
        on_time_delivery_rate = (on_time_delivered_pos.count() / completed_pos.count()) * 100 if completed_pos.count() > 0 else 0.0

        # Quality Rating Average
        completed_pos_with_rating = completed_pos.exclude(quality_rating__isnull=True)
        quality_rating_avg = completed_pos_with_rating.aggregate(Avg('quality_rating'))['quality_rating__avg'] if completed_pos_with_rating.count() > 0 else 0.0

        # Average Response Time
        acknowledged_pos = completed_pos.exclude(acknowledgment_date__isnull=True)
        avg_response_time = acknowledged_pos.aggregate(Avg('acknowledgment_date' - F('issue_date')))['acknowledgment_date__avg'].total_seconds() if acknowledged_pos.count() > 0 else 0.0

        # Fulfilment Rate
        fulfilled_pos = completed_pos.exclude(issue_date__isnull=True)
        fulfilment_rate = (fulfilled_pos.count() / completed_pos.count()) * 100 if completed_pos.count() > 0 else 0.0

        # Update or create historical performance record
        historical_performance, created = HistoricalPerformance.objects.update_or_create(
            vendor=vendor,
            date=timezone.now(),
            defaults={
                'on_time_delivery_rate': on_time_delivery_rate,
                'quality_rating_avg': quality_rating_avg,
                'average_response_time': avg_response_time,
                'fulfilment_rate': fulfilment_rate
            }
        )

        # Update vendor performance metrics in the Vendor model
        vendor.on_time_delivery_rate = historical_performance.on_time_delivery_rate
        vendor.quality_rating_avg = historical_performance.quality_rating_avg
        vendor.average_response_time = historical_performance.average_response_time
        vendor.fulfillment_rate = historical_performance.fulfillment_rate
        vendor.save()

class VendorPerformanceView(generics.RetrieveAPIView):
    queryset = Vendor.objects.all()
    serializer_class = HistoricalPerformanceSerializer
