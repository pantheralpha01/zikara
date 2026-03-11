from pydantic import BaseModel


class OtpSendRequest(BaseModel):
    phone: str


class OtpVerifyRequest(BaseModel):
    phone: str
    code: str


class OtpSendResponse(BaseModel):
    message: str


class OtpVerifyResponse(BaseModel):
    verified: bool
    message: str
