from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_user_fcm_token_and_userfcmtoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="height",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
