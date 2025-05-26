from django.db import models

class AlcaldiaVista(models.Model):
    Estado = models.CharField(max_length=100)
    Alcaldia = models.CharField(max_length=100)
    colonia = models.CharField(max_length=100)
    Promedio_MXN = models.DecimalField(max_digits=10, decimal_places=2)
    zona = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.colonia} - {self.Alcaldia}"


    class Meta:
        managed = False
        db_table = 'alcaldia_vistas'

