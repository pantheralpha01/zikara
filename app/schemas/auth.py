from typing import Optional
from pydantic import BaseModel, EmailStr


class ClientSignupRequest(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    phone: str


class AgentApplyRequest(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    phone: str
    idNumber: str
    idType: str


class PartnerSignupRequest(BaseModel):
    contactFirstName: str
    contactLastName: str
    email: EmailStr
    password: str
    phone: str
    idNumber: str
    idType: str
    businessName: str
    website: str
    description: str


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
