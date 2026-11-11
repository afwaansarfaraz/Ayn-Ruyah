"""Custom domain exceptions for RetinaLens AI."""

class RetinaLensException(Exception):
    """Base exception for application errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidRetinalImageError(RetinaLensException):
    """Raised when an uploaded image fails fundus validation checks."""
    def __init__(self, message: str = "Image does not appear to be a valid retinal fundus scan."):
        super().__init__(message, status_code=400)


class ModelNotLoadedError(RetinaLensException):
    """Raised when inference is requested but no model weights are available."""
    def __init__(self, message: str = "Diabetic Retinopathy model weights are not loaded."):
        super().__init__(message, status_code=503)


class InferenceError(RetinaLensException):
    """Raised when an error occurs during model forward pass or Grad-CAM generation."""
    def __init__(self, message: str = "An error occurred during image diagnostic inference."):
        super().__init__(message, status_code=500)


class ConfigurationError(RetinaLensException):
    """Raised when configuration or database setup is invalid."""
    def __init__(self, message: str = "Configuration error."):
        super().__init__(message, status_code=500)


class TenantNotFoundError(RetinaLensException):
    """Raised when tenant/hospital workspace cannot be found."""
    def __init__(self, message: str = "Hospital workspace not found."):
        super().__init__(message, status_code=404)


class PatientNotFoundError(RetinaLensException):
    """Raised when a patient record is not found."""
    def __init__(self, message: str = "Patient record not found."):
        super().__init__(message, status_code=404)


class AuthenticationError(RetinaLensException):
    """Raised when credentials fail authentication."""
    def __init__(self, message: str = "Invalid credentials."):
        super().__init__(message, status_code=401)


class AuthorizationError(RetinaLensException):
    """Raised when user role lacks permission for the action."""
    def __init__(self, message: str = "Access denied."):
        super().__init__(message, status_code=403)


class DuplicatePatientError(RetinaLensException):
    """Raised when attempting to register a duplicate patient within the same tenant workspace."""
    def __init__(self, message: str = "A patient with this name and date of birth or phone number already exists in this hospital workspace."):
        super().__init__(message, status_code=409)



