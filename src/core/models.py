from django.db import models
import uuid

class Event(models.Model):
    EVENT_TYPES = [
        ('product_viewed','Producto visto'),
        ('product_added_to_cart','Agregado al carrito'),
        ('purchase_completed','Compra completada'),
        ('user_registered','Usuario registrado'),
        ('purchase_cancelled','Compra cancelada')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    payload = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    processed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['processed','created_at']),
        ]
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.event_type} @ {self.timestamp.isoformat()}"
    
class Reporte(models.Model):
    STATUS_CHOICES = [
        ('pending','Pendiente'),
        ('processing','Procesando'),
        ('completed','Completado'),
        ('failed','Fallido'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=50)
    parameters = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_path = models.CharField(max_length=500, blank=True, null=True)
    result_data = models.JSONField(default=dict,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Reporte {self.report_type} ({self.status})"
    

class Alerta(models.Model):
    SEVERITY_CHOICES = [
        ('low','Baja'),
        ('medium','Media'),
        ('high','Alta'),
        ('critical','Critica')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert_type = models.CharField(max_length=50)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True,blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Alerta {self.alert_type} ({self.severity})"
    
