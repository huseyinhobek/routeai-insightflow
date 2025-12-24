"""
Email service for sending verification codes and notifications
Native Insight Studio - Professional Email Templates
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Email configuration from environment
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "Native Insight Studio <noreply@nativeag.io>")
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

# Branding
BRAND_NAME = "Native Insight Studio"
BRAND_COLOR_PRIMARY = "#2563EB"
BRAND_COLOR_SECONDARY = "#4F46E5"
BRAND_COLOR_DARK = "#1E3A8A"
COMPANY_NAME = "Native AI"
COMPANY_WEBSITE = "https://nativeag.io"
CURRENT_YEAR = "2024"

# Logo URL - hosted on the frontend (public folder, no hash)
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://n8n.n0ps.net/sav-insight")
LOGO_URL = f"{APP_BASE_URL}/native-logo.png"


def _get_email_header() -> str:
    """Professional email header with Native AI branding and logo"""
    return f"""
    <div style="background: linear-gradient(135deg, {BRAND_COLOR_PRIMARY}, {BRAND_COLOR_SECONDARY}); padding: 32px 20px; text-align: center; border-radius: 12px 12px 0 0;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
                <td align="center">
                    <div style="display: inline-block; background: white; padding: 16px 24px; border-radius: 12px; margin-bottom: 16px;">
                        <img src="{LOGO_URL}" alt="{COMPANY_NAME}" style="height: 40px; width: auto; vertical-align: middle;" />
                    </div>
                </td>
            </tr>
            <tr>
                <td align="center">
                    <p style="color: white; font-size: 20px; font-weight: 600; margin: 8px 0 4px 0;">{BRAND_NAME}</p>
                    <p style="color: rgba(255,255,255,0.85); font-size: 13px; margin: 0;">Powered by {COMPANY_NAME}</p>
                </td>
            </tr>
        </table>
    </div>
    """


def _get_email_footer() -> str:
    """Professional email footer"""
    return f"""
    <div style="background: #F8FAFC; padding: 24px 20px; text-align: center; border-top: 1px solid #E2E8F0; border-radius: 0 0 12px 12px;">
        <p style="color: #64748B; font-size: 12px; margin: 0 0 8px 0;">
            This email was sent automatically by {BRAND_NAME}.
        </p>
        <p style="color: #64748B; font-size: 12px; margin: 0 0 8px 0;">
            If you didn't request this, you can safely ignore this email.
        </p>
        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #E2E8F0;">
            <p style="color: #94A3B8; font-size: 11px; margin: 0;">
                © {CURRENT_YEAR} {COMPANY_NAME}. All rights reserved.
            </p>
            <p style="color: #94A3B8; font-size: 11px; margin: 4px 0 0 0;">
                <a href="{COMPANY_WEBSITE}" style="color: {BRAND_COLOR_PRIMARY}; text-decoration: none;">nativeag.io</a>
            </p>
        </div>
    </div>
    """


def _get_base_template(content: str) -> str:
    """Wrap content in professional email template"""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{BRAND_NAME}</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #F1F5F9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #F1F5F9; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                        <tr>
                            <td>
                                {_get_email_header()}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 32px 40px;">
                                {content}
                            </td>
                        </tr>
                        <tr>
                            <td>
                                {_get_email_footer()}
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def send_otp_email(
    to_email: str,
    otp_code: str,
    user_name: Optional[str] = None,
) -> bool:
    """
    Send OTP verification code email.
    
    Args:
        to_email: Recipient email address
        otp_code: 6-digit OTP code
        user_name: Optional user name for personalization
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not EMAIL_ENABLED:
        logger.info(f"[EMAIL DISABLED] OTP for {to_email}: {otp_code}")
        return True
    
    if not SMTP_HOST or not SMTP_USER:
        logger.warning("SMTP not configured, cannot send email")
        return False
    
    subject = f"{BRAND_NAME} - Your Verification Code"
    
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    
    content = f"""
        <h2 style="color: #1E293B; font-size: 20px; font-weight: 600; margin: 0 0 16px 0;">
            {greeting}
        </h2>
        
        <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
            Use the verification code below to sign in to {BRAND_NAME}:
        </p>
        
        <div style="background: linear-gradient(135deg, {BRAND_COLOR_PRIMARY}, {BRAND_COLOR_SECONDARY}); padding: 28px 40px; border-radius: 12px; text-align: center; margin: 24px 0;">
            <span style="font-size: 36px; font-weight: 700; color: white; letter-spacing: 10px; font-family: 'SF Mono', 'Roboto Mono', monospace;">
                {otp_code}
            </span>
        </div>
        
        <div style="background: #FEF3C7; border-left: 4px solid #F59E0B; padding: 16px; border-radius: 0 8px 8px 0; margin: 24px 0;">
            <p style="color: #92400E; font-size: 14px; margin: 0; font-weight: 500;">
                ⏱️ This code expires in <strong>10 minutes</strong>.
            </p>
        </div>
        
        <p style="color: #64748B; font-size: 14px; line-height: 1.6; margin: 24px 0 0 0;">
            If you didn't request this code, please ignore this email or contact support if you have concerns about your account security.
        </p>
    """
    
    html_content = _get_base_template(content)
    
    text_content = f"""
{greeting}

Use the verification code below to sign in to {BRAND_NAME}:

{otp_code}

This code expires in 10 minutes.

If you didn't request this code, please ignore this email.

---
{BRAND_NAME}
Powered by {COMPANY_NAME}
    """
    
    return _send_email(to_email, subject, html_content, text_content)


def send_invite_email(
    to_email: str,
    invite_url: str,
    org_name: str,
    inviter_name: str,
    role: str,
) -> bool:
    """
    Send organization invitation email.
    
    Args:
        to_email: Recipient email address
        invite_url: Invitation URL with token
        org_name: Organization name
        inviter_name: Name of the person who sent the invite
        role: Role being assigned
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not EMAIL_ENABLED:
        logger.info(f"[EMAIL DISABLED] Invite for {to_email} to {org_name}: {invite_url}")
        return True
    
    if not SMTP_HOST or not SMTP_USER:
        logger.warning("SMTP not configured, cannot send email")
        return False
    
    subject = f"{BRAND_NAME} - You've been invited to {org_name}"
    
    role_display = {
        "super_admin": "Super Admin",
        "org_admin": "Organization Admin",
        "transformer": "Transformer",
        "reviewer": "Reviewer",
        "viewer": "Viewer",
    }.get(role, role.replace("_", " ").title())
    
    content = f"""
        <h2 style="color: #1E293B; font-size: 20px; font-weight: 600; margin: 0 0 16px 0;">
            You've been invited! 🎉
        </h2>
        
        <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
            <strong>{inviter_name}</strong> has invited you to join <strong>{org_name}</strong> on {BRAND_NAME}.
        </p>
        
        <div style="background: #F0F9FF; border: 1px solid #BAE6FD; padding: 20px 24px; border-radius: 12px; margin: 24px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td style="padding: 8px 0;">
                        <span style="color: #64748B; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Organization</span>
                        <p style="color: #0F172A; font-size: 16px; font-weight: 600; margin: 4px 0 0 0;">{org_name}</p>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;">
                        <span style="color: #64748B; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Your Role</span>
                        <p style="color: #0F172A; font-size: 16px; font-weight: 600; margin: 4px 0 0 0;">{role_display}</p>
                    </td>
                </tr>
            </table>
        </div>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{invite_url}" style="display: inline-block; background: linear-gradient(135deg, {BRAND_COLOR_PRIMARY}, {BRAND_COLOR_SECONDARY}); color: white; font-size: 16px; font-weight: 600; padding: 16px 40px; border-radius: 8px; text-decoration: none; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);">
                Accept Invitation
            </a>
        </div>
        
        <div style="background: #FEF3C7; border-left: 4px solid #F59E0B; padding: 16px; border-radius: 0 8px 8px 0; margin: 24px 0;">
            <p style="color: #92400E; font-size: 14px; margin: 0; font-weight: 500;">
                ⏱️ This invitation expires in <strong>24 hours</strong>.
            </p>
        </div>
        
        <p style="color: #64748B; font-size: 13px; line-height: 1.6; margin: 24px 0 0 0;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{invite_url}" style="color: {BRAND_COLOR_PRIMARY}; word-break: break-all;">{invite_url}</a>
        </p>
    """
    
    html_content = _get_base_template(content)
    
    text_content = f"""
You've been invited!

{inviter_name} has invited you to join {org_name} on {BRAND_NAME}.

Organization: {org_name}
Your Role: {role_display}

Accept your invitation:
{invite_url}

This invitation expires in 24 hours.

---
{BRAND_NAME}
Powered by {COMPANY_NAME}
    """
    
    return _send_email(to_email, subject, html_content, text_content)


def send_password_set_email(
    to_email: str,
    set_password_url: str,
    user_name: Optional[str] = None,
    org_name: Optional[str] = None,
) -> bool:
    """
    Send email to set password for new invited users.
    
    Args:
        to_email: Recipient email address
        set_password_url: URL to set password
        user_name: Optional user name
        org_name: Optional organization name
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not EMAIL_ENABLED:
        logger.info(f"[EMAIL DISABLED] Set password for {to_email}: {set_password_url}")
        return True
    
    if not SMTP_HOST or not SMTP_USER:
        logger.warning("SMTP not configured, cannot send email")
        return False
    
    subject = f"{BRAND_NAME} - Set Your Password"
    
    greeting = f"Hi {user_name}," if user_name else "Hi there,"
    org_text = f" for {org_name}" if org_name else ""
    
    content = f"""
        <h2 style="color: #1E293B; font-size: 20px; font-weight: 600; margin: 0 0 16px 0;">
            {greeting}
        </h2>
        
        <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
            Your account{org_text} has been created. Click the button below to set your password:
        </p>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{set_password_url}" style="display: inline-block; background: linear-gradient(135deg, {BRAND_COLOR_PRIMARY}, {BRAND_COLOR_SECONDARY}); color: white; font-size: 16px; font-weight: 600; padding: 16px 40px; border-radius: 8px; text-decoration: none; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);">
                Set Password
            </a>
        </div>
        
        <div style="background: #FEF3C7; border-left: 4px solid #F59E0B; padding: 16px; border-radius: 0 8px 8px 0; margin: 24px 0;">
            <p style="color: #92400E; font-size: 14px; margin: 0; font-weight: 500;">
                ⏱️ This link expires in <strong>24 hours</strong>.
            </p>
        </div>
        
        <p style="color: #64748B; font-size: 13px; line-height: 1.6; margin: 24px 0 0 0;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{set_password_url}" style="color: {BRAND_COLOR_PRIMARY}; word-break: break-all;">{set_password_url}</a>
        </p>
    """
    
    html_content = _get_base_template(content)
    
    text_content = f"""
{greeting}

Your account{org_text} has been created. Use the link below to set your password:

{set_password_url}

This link expires in 24 hours.

---
{BRAND_NAME}
Powered by {COMPANY_NAME}
    """
    
    return _send_email(to_email, subject, html_content, text_content)


def send_magic_link_email(
    to_email: str,
    magic_link_url: str,
    user_name: Optional[str] = None,
) -> bool:
    """
    Legacy function - deprecated, use OTP instead.
    """
    if not EMAIL_ENABLED:
        logger.info(f"[EMAIL DISABLED] Magic link for {to_email}: {magic_link_url}")
        return True
    
    return False


def send_credentials_email(
    to_email: str,
    user_name: str,
    temp_password: str,
    login_url: str,
    org_name: str,
    role: str,
) -> bool:
    """
    Send login credentials to a user.
    
    Args:
        to_email: Recipient email address
        user_name: User's name
        temp_password: Temporary password
        login_url: Login page URL
        org_name: Organization name
        role: User role
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not EMAIL_ENABLED:
        logger.info(f"[EMAIL DISABLED] Credentials for {to_email}: Password={temp_password}")
        return True
    
    if not SMTP_HOST or not SMTP_USER:
        logger.warning("SMTP not configured, cannot send email")
        return False
    
    subject = f"{BRAND_NAME} - Your Login Credentials"
    
    role_display = {
        "super_admin": "Super Admin",
        "org_admin": "Organization Admin",
        "transformer": "Transformer",
        "reviewer": "Reviewer",
        "viewer": "Viewer",
    }.get(role, role.replace("_", " ").title())
    
    content = f"""
        <h2 style="color: #1E293B; font-size: 20px; font-weight: 600; margin: 0 0 16px 0;">
            Welcome to {BRAND_NAME}! 🎉
        </h2>
        
        <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
            Hi {user_name}, your account has been created. Here are your login credentials:
        </p>
        
        <div style="background: #F0F9FF; border: 1px solid #BAE6FD; padding: 24px; border-radius: 12px; margin: 24px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td style="padding: 8px 0;">
                        <span style="color: #64748B; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Organization</span>
                        <p style="color: #0F172A; font-size: 16px; font-weight: 600; margin: 4px 0 0 0;">{org_name}</p>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;">
                        <span style="color: #64748B; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Your Role</span>
                        <p style="color: #0F172A; font-size: 16px; font-weight: 600; margin: 4px 0 0 0;">{role_display}</p>
                    </td>
                </tr>
            </table>
        </div>
        
        <div style="background: linear-gradient(135deg, {BRAND_COLOR_DARK}, {BRAND_COLOR_PRIMARY}); padding: 24px; border-radius: 12px; margin: 24px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td style="padding: 8px 0;">
                        <span style="color: rgba(255,255,255,0.8); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Email</span>
                        <p style="color: white; font-size: 16px; font-weight: 600; margin: 4px 0 0 0; font-family: 'SF Mono', 'Roboto Mono', monospace;">{to_email}</p>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 12px 0 8px 0;">
                        <span style="color: rgba(255,255,255,0.8); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Password</span>
                        <p style="color: white; font-size: 20px; font-weight: 700; margin: 4px 0 0 0; font-family: 'SF Mono', 'Roboto Mono', monospace; letter-spacing: 1px;">{temp_password}</p>
                    </td>
                </tr>
            </table>
        </div>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{login_url}" style="display: inline-block; background: linear-gradient(135deg, {BRAND_COLOR_PRIMARY}, {BRAND_COLOR_SECONDARY}); color: white; font-size: 16px; font-weight: 600; padding: 16px 40px; border-radius: 8px; text-decoration: none; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);">
                Login Now
            </a>
        </div>
        
        <div style="background: #FEF3C7; border-left: 4px solid #F59E0B; padding: 16px; border-radius: 0 8px 8px 0; margin: 24px 0;">
            <p style="color: #92400E; font-size: 14px; margin: 0; font-weight: 500;">
                🔐 For your security, please change your password after your first login.
            </p>
        </div>
        
        <p style="color: #64748B; font-size: 13px; line-height: 1.6; margin: 24px 0 0 0;">
            If the button doesn't work, visit:<br>
            <a href="{login_url}" style="color: {BRAND_COLOR_PRIMARY}; word-break: break-all;">{login_url}</a>
        </p>
    """
    
    html_content = _get_base_template(content)
    
    text_content = f"""
Welcome to {BRAND_NAME}!

Hi {user_name}, your account has been created. Here are your login credentials:

Organization: {org_name}
Your Role: {role_display}

Email: {to_email}
Password: {temp_password}

Login here: {login_url}

For your security, please change your password after your first login.

---
{BRAND_NAME}
Powered by {COMPANY_NAME}
    """
    
    return _send_email(to_email, subject, html_content, text_content)


def _send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str,
) -> bool:
    """
    Internal function to send email via SMTP.
    
    Args:
        to_email: Recipient email
        subject: Email subject
        html_content: HTML body
        text_content: Plain text body
    
    Returns:
        True if sent successfully
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        
        # Attach both plain text and HTML versions
        part1 = MIMEText(text_content, "plain", "utf-8")
        part2 = MIMEText(html_content, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)
        
        # Connect and send
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, to_email, msg.as_string())
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
