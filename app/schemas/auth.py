from typing import List, Optional

from pydantic import BaseModel, EmailStr

from app.models.profile import ComputerExperience, EducationLevel, EnglishLevel, IdType
from app.models.user import Gender


class ClientSignupRequest(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    phone: str
    gender: Optional[Gender] = None
    profilePicUrl: Optional[str] = None


class AgentApplyRequest(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    phone: str
    idNumber: str
    idType: IdType
    gender: Optional[Gender] = None
    profilePicUrl: Optional[str] = None
    age: Optional[int] = None
    town: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    educationLevel: Optional[EducationLevel] = None
    englishLevel: Optional[EnglishLevel] = None
    computerExperience: Optional[ComputerExperience] = None
    haveAComputer: Optional[bool] = None
    accessToInternet: Optional[bool] = None
    internetSpeed: Optional[str] = None
    descriptionOfSelf: Optional[str] = None


class PartnerSignupRequest(BaseModel):
    contactFirstName: str
    contactLastName: str
    email: EmailStr
    password: str
    phone: str
    idNumber: str
    idType: IdType
    businessName: str
    website: Optional[str] = None
    description: Optional[str] = None
    gender: Optional[Gender] = None
    profilePicUrl: Optional[str] = None
    servicesProvided: Optional[List[str]] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str


class RefreshRequest(BaseModel):
    refreshToken: str


class AccessTokenResponse(BaseModel):
    accessToken: str
