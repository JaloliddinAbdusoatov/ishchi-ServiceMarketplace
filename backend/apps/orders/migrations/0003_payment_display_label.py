from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("orders", "0002_serviceorder_assigned_workers_serviceorder_capacity_and_more")]
    operations = [migrations.AlterField(model_name="serviceorder", name="payment_status",
        field=models.CharField(choices=[("DISABLED", "Payments unavailable")], default="DISABLED", max_length=20))]
