from django.db import models

class MetaPortfolio(models.Model):
    """
    Business Manager level - groups ad accounts
    """
    portfolio_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.portfolio_id})"

class MetaAdAccount(models.Model):
    """
    Ad Account level - groups campaigns
    """
    portfolio = models.ForeignKey(MetaPortfolio, on_delete=models.CASCADE, related_name='ad_accounts')
    account_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50)
    currency = models.CharField(max_length=3)
    timezone = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.account_id})"

class MetaCampaign(models.Model):
    """
    Campaign level - where budgets are set
    """
    account = models.ForeignKey(MetaAdAccount, on_delete=models.CASCADE, related_name='campaigns')
    campaign_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50)
    daily_budget = models.DecimalField(max_digits=10, decimal_places=2)
    budget_optimization = models.BooleanField(default=True)  # Is CBO enabled?
    objective = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.campaign_id})"

class MetaAdSet(models.Model):
    """
    Ad Set level - targeting and delivery settings
    """
    campaign = models.ForeignKey(MetaCampaign, on_delete=models.CASCADE, related_name='adsets')
    adset_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50)
    targeting = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.adset_id})"

class MetaSpend(models.Model):
    """
    Daily spend and performance metrics
    """
    date = models.DateField(db_index=True)
    campaign = models.ForeignKey(MetaCampaign, on_delete=models.CASCADE, related_name='spend_records')
    adset = models.ForeignKey(MetaAdSet, on_delete=models.CASCADE, related_name='spend_records')
    spend = models.DecimalField(max_digits=10, decimal_places=2)
    impressions = models.IntegerField()
    clicks = models.IntegerField()
    ctr = models.DecimalField(max_digits=5, decimal_places=2)
    cpc = models.DecimalField(max_digits=10, decimal_places=2)
    conversions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['date', 'campaign', 'adset']
        indexes = [
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.campaign.name} - {self.adset.name} - {self.date} - ${self.spend}"
