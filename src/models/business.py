from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

@dataclass
class BusinessHours:
    day: str
    open_time: Optional[str]
    close_time: Optional[str]
    is_closed: bool = False

@dataclass
class SocialMediaLinks:
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None

@dataclass
class Business:
    name: str
    category: str
    address: str
    source: str = "Unknown"  # Move this before the default arguments
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    social_media: Optional[SocialMediaLinks] = field(default_factory=SocialMediaLinks)
    hours: Optional[List[BusinessHours]] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    last_updated: datetime = field(default_factory=datetime.now)

    def validate(self) -> bool:
        """Basic validation of business data"""
        if not self.name or not self.address:
            return False
        if self.phone and not self._validate_phone():
            return False
        if self.email and not self._validate_email():
            return False
        return True

    def _validate_phone(self) -> bool:
        # Remove all non-numeric characters
        clean_phone = ''.join(filter(str.isdigit, self.phone))
        return len(clean_phone) >= 8

    def _validate_email(self) -> bool:
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, self.email))
