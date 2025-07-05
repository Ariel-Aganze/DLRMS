from django.utils import timezone
from core.models import AuditLog
from django.contrib.auth import get_user_model
import random

User = get_user_model()

def create_sample_audit_logs():
    """
    Creates sample audit logs for testing the reports system.
    Returns the number of logs created.
    """
    # Get users
    users = User.objects.all()
    
    if not users.exists():
        return 0
            
    # Sample descriptions for different action types
    descriptions = {
        'login': ['User logged in from admin panel', 'User logged in from mobile app'],
        'logout': ['User logged out from admin panel', 'Session expired'],
        'create': ['Created new land title', 'Added new user account', 'Created new certificate'],
        'update': ['Updated user profile', 'Modified land boundaries', 'Updated certificate details'],
        'view': ['Viewed certificate details', 'Accessed user profile', 'Viewed land title'],
        'download': ['Downloaded certificate PDF', 'Downloaded land title', 'Downloaded report'],
        'upload': ['Uploaded supporting document', 'Uploaded profile picture', 'Uploaded land survey'],
        'approve': ['Approved land title request', 'Approved user registration'],
        'reject': ['Rejected land title application', 'Rejected document upload'],
        'transfer': ['Transferred land ownership', 'Transferred user responsibility'],
        'sign': ['Digitally signed certificate', 'Signed land transfer document'],
        'other': ['System maintenance performed', 'Database backup completed'],
    }
    
    # Generate timestamps (including some from today)
    now = timezone.now()
    today = now.date()
    
    # Create 50 sample logs with various timestamps over the past month
    created_count = 0
    for i in range(50):
        # Randomly select action type
        action_type = random.choice(list(descriptions.keys()))
        
        # Random timestamp within the past month
        days_ago = random.randint(0, 30)
        timestamp = now - timezone.timedelta(days=days_ago, 
                                            hours=random.randint(0, 23), 
                                            minutes=random.randint(0, 59))
        
        # Randomly select a user
        user = random.choice(users)
        
        # Object types
        object_types = ['Land', 'Certificate', 'User', 'Document', 'Application']
        object_type = random.choice(object_types) if random.random() > 0.3 else None
        
        # Create the log
        AuditLog.objects.create(
            user=user,
            action_type=action_type,
            description=random.choice(descriptions[action_type]),
            ip_address=f"192.168.1.{random.randint(1, 255)}",
            user_agent=f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.{random.randint(1000, 9999)}.0 Safari/537.36",
            session_key=f"session_{random.randint(10000, 99999)}",
            object_type=object_type,
            object_id=random.randint(1, 100) if object_type else None,
            object_repr=f"{object_type} #{random.randint(1, 100)}" if object_type else None,
            success=random.random() > 0.1,  # 90% success rate
            timestamp=timestamp
        )
        created_count += 1
    
    # Add some logs specifically for today to show in "Active Users Today"
    for i in range(5):
        user = random.choice(users)
        AuditLog.objects.create(
            user=user,
            action_type='login',
            description='User logged in',
            ip_address=f"192.168.1.{random.randint(1, 255)}",
            user_agent=f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.{random.randint(1000, 9999)}.0 Safari/537.36",
            session_key=f"session_{random.randint(10000, 99999)}",
            success=True,
            timestamp=now - timezone.timedelta(hours=random.randint(0, 8))
        )
        created_count += 1
            
    return created_count