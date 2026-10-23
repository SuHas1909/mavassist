from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import re

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Register(Input):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=72)
    @field_validator('email')
    @classmethod
    def email_valid(cls, v):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', v): raise ValueError('Enter a valid email address')
        return v.lower()
    @field_validator('password')
    @classmethod
    def password_bytes(cls, v):
        if len(v.encode()) > 72: raise ValueError('Password must be at most 72 UTF-8 bytes')
        return v
class Login(Input):
    email: str = Field(max_length=254)
    password: str = Field(max_length=72)
class ServiceInput(Input):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=3000)
    category_id: int = Field(gt=0)
    location: str = Field(min_length=2, max_length=250)
    hours: str = Field(min_length=2, max_length=250)
    contact: str = Field(min_length=2, max_length=250)
    source_url: str = Field(max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=20)
    next_steps: list[str] = Field(min_length=2, max_length=3)
    active: bool = True
    verified: bool = False
    @field_validator('source_url')
    @classmethod
    def source_safe(cls, v):
        if not v.startswith('https://'): raise ValueError('Source URL must use HTTPS')
        return v
    @field_validator('tags', 'next_steps')
    @classmethod
    def bounded_strings(cls, v):
        if any(not x.strip() or len(x)>300 for x in v): raise ValueError('Each item must contain 1-300 characters')
        return v
class ActiveInput(Input): active: bool
class CategoryInput(Input): name: str = Field(min_length=2, max_length=80)
class NoticeInput(Input):
    service_id: int = Field(gt=0)
    title: str = Field(min_length=2, max_length=160)
    body: str = Field(min_length=2, max_length=2000)
    starts_at: datetime
    ends_at: datetime
    @model_validator(mode='after')
    def dates(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None: raise ValueError('Dates require timezone offsets')
        if self.ends_at<=self.starts_at: raise ValueError('End must be after start')
        return self
class ConversationTurn(Input):
    question: str = Field(min_length=1,max_length=1000)
    answer: str = Field(max_length=4000)
class Question(Input):
    text: str = Field(min_length=2, max_length=1000)
    history: list[ConversationTurn] = Field(default_factory=list,max_length=3)
class Feedback(Input): helpful: bool
