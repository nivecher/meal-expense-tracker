# Email Configuration Guide

The Meal Expense Tracker supports email notifications for password resets and user management. You can configure email using either SMTP or AWS SES (Simple Email Service).

## Quick Setup

### Option 1: Disable Email (Default)

Email is disabled by default. Password resets will be logged to the application logs instead of sent via email.

```bash
# Email is disabled by default - no configuration needed
```

### Option 2: AWS SES (Recommended for Production)

AWS SES is ideal for production applications as it doesn't require a personal email address and provides reliable delivery.

#### Step 1: Set up AWS SES

1. **Create AWS Account** (if you don't have one)
2. **Verify Your Domain** (Recommended for nivecher.com):
   - Go to AWS SES Console
   - Navigate to "Verified identities"
   - Click "Create identity" → "Domain"
   - Enter `nivecher.com`
   - Choose "Easy DKIM" for automatic DNS record creation
   - Add the provided DNS records to your Route 53 hosted zone
   - This allows sending from any email address at your domain
3. **Verify Email Addresses** (for testing or if not using domain verification):
   - Add and verify specific email addresses you want to send to
4. **Request Production Access**:
   - In SES Console, go to "Account dashboard"
   - Click "Request production access" to send to any email address

#### Step 2: Configure Environment Variables

**AWS SES with IAM Role (Recommended):**

```bash
export MAIL_ENABLED=true
export AWS_SES_REGION=us-east-1
export MAIL_DEFAULT_SENDER=noreply@nivecher.com
```

The application automatically uses IAM roles for AWS SES authentication - no access keys needed!

#### Step 3: Route 53 DNS Configuration (for nivecher.com)

Since you own the nivecher.com domain and Route 53 DNS zones, you can easily set up domain verification:

1. **In AWS SES Console**:

   - After creating the domain identity, you'll see DNS records to add
   - Copy the DKIM CNAME records (usually 3 records)

2. **In Route 53 Console**:

   - Go to your nivecher.com hosted zone
   - Create the DKIM CNAME records provided by SES
   - Wait for DNS propagation (usually 5-10 minutes)

3. **Benefits of Domain Verification**:
   - Send from any email address at nivecher.com
   - Better email deliverability
   - Professional appearance
   - No need to verify individual email addresses

#### Step 4: IAM Permissions

Ensure your IAM role has these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ses:SendEmail", "ses:SendRawEmail"],
      "Resource": "*"
    }
  ]
}
```

### Option 3: Disable Email (Development)

For development without email functionality:

```bash
# Email is disabled by default - no configuration needed
# Password resets will be logged to application logs
```

## Email Features

### Password Reset Emails

- Sent when admin resets a user's password
- Contains secure temporary password
- Includes security warnings and instructions

### Welcome Emails

- Sent to new users when created by admin
- Contains login credentials
- Includes app introduction and features

### Email Addresses for nivecher.com

With domain verification, you can send from any address at your domain:

- `noreply@nivecher.com` - For system notifications
- `admin@nivecher.com` - For admin communications
- `support@nivecher.com` - For user support
- `alerts@nivecher.com` - For system alerts

### Email Templates

- Professional HTML templates
- Mobile-responsive design
- Security-focused messaging
- Branded with your app name

## Testing Email Configuration

### Test with AWS SES

```python
from app.services.email_service import send_test_email, is_email_enabled

if is_email_enabled():
    success = send_test_email("test@example.com")
    print(f"Test email sent: {success}")
else:
    print("Email is disabled")
```

### Check Email Status

```python
from app.services.email_service import is_email_enabled

print(f"Email enabled: {is_email_enabled()}")
```

## Troubleshooting

### Common Issues

1. **"Email is disabled" message**

   - Set `MAIL_ENABLED=true` in environment variables

2. **AWS SES "Access Denied"**

   - Check IAM role permissions
   - Ensure SES is available in your region
   - Verify the IAM role is attached to your service

3. **SES Configuration Issues**

   - Verify IAM role has SES permissions
   - Check AWS region configuration
   - Ensure domain is verified in SES

4. **Emails not delivered**
   - Check spam folder
   - Verify sender email address
   - Check SES sending limits

### Logs

Email attempts are logged with details:

- Success: `INFO` level
- Failures: `ERROR` level
- Disabled: `WARNING` level

## Security Considerations

1. **Uses IAM roles by default** - no credentials to manage
2. **Verify sender domains** in SES for better deliverability
3. **Monitor sending limits** to avoid rate limiting
4. **Use HTTPS** for all email-related configurations
5. **Principle of least privilege** - IAM roles only have SES permissions

## Cost Considerations

### AWS SES Pricing (2024)

#### Free Tier

- **62,000 emails/month** when sent from EC2 instances
- **200 emails/day** when sent from other sources
- **No cost** for the first 62,000 emails if using EC2

#### Pay-as-you-go Pricing

- **$0.10 per 1,000 emails** (after free tier)
- **$0.12 per 1,000 emails** for attachments
- **No setup fees** or monthly charges
- **No minimum commitment**

#### Real-world Cost Examples

For a meal expense tracker application:

**Small Usage (100 users, 2 emails/month each)**:

- 200 emails/month = **$0.00** (within free tier)
- Annual cost: **$0**

**Medium Usage (1,000 users, 5 emails/month each)**:

- 5,000 emails/month = **$0.00** (within free tier)
- Annual cost: **$0**

**Large Usage (10,000 users, 10 emails/month each)**:

- 100,000 emails/month = 38,000 paid emails = **$3.80/month**
- Annual cost: **$45.60**

**Enterprise Usage (100,000 users, 20 emails/month each)**:

- 2,000,000 emails/month = 1,938,000 paid emails = **$193.80/month**
- Annual cost: **$2,325.60**

### Alternative Email Services

- **Gmail SMTP**: Free (500 emails/day limit) - not supported in this app
- **Outlook SMTP**: Free (300 emails/day limit) - not supported in this app
- **Other providers**: $5-50/month for business plans - not supported in this app

## Production Recommendations

1. **Use AWS SES** for production applications
2. **IAM roles are configured by default** - no additional setup needed
3. **Domain verification with nivecher.com** - professional email delivery
4. **Route 53 integration** - easy DNS management for DKIM records
5. **Monitor email delivery** and bounce rates
6. **Set up CloudWatch alarms** for email failures
7. **Use separate SES configurations** for different environments
8. **Consider SPF and DMARC records** for additional email security
