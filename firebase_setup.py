"""
Firebase Admin SDK initialization and Firestore client setup.
Critical: All state management flows through Firestore for observability.
"""
import firebase_admin
from firebase_admin import credentials, firestore, exceptions
from typing import Optional
from loguru import logger
import sys

from config import settings

class FirebaseManager:
    """Singleton manager for Firebase services with robust error handling."""
    
    _instance: Optional['FirebaseManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.app = None
            self.db: Optional[firestore.Client] = None
            self._initialize()
            self._initialized = True
    
    def _initialize(self) -> None:
        """Initialize Firebase Admin SDK with comprehensive error handling."""
        try:
            # Check if already initialized
            if firebase_admin._apps:
                logger.info("Firebase already initialized, using existing app")
                self.app = firebase_admin.get_app()
            else:
                logger.info(f"Initializing Firebase with credentials: {settings.FIREBASE_CREDENTIALS_PATH}")
                cred = credentials.Certificate(str(settings.FIREBASE_CREDENTIALS_PATH))
                
                # Initialize with specific project ID for clarity
                self.app = firebase_admin.initialize_app(
                    cred,
                    {
                        'projectId': settings.FIREBASE_PROJECT_ID,
                    },
                    name='predatory_velocity'  # Named app to avoid conflicts
                )
            
            # Initialize Firestore client
            self.db = firestore.client(app=self.app)
            
            # Test connection with a simple document read
            test_ref = self.db.collection('system_health').document('connection_test')
            test_ref.set({'test': True, 'timestamp': firestore.SERVER_TIMESTAMP})
            test_ref.delete()
            
            logger.success("Firebase initialized successfully")
            
        except FileNotFoundError as e:
            logger.critical(f"Firebase credentials file not found: {e}")
            sys.exit(1)
        except ValueError as e:
            logger.critical(f"Invalid Firebase credentials: {e}")
            sys.exit(1)
        except exceptions.FirebaseError as e:
            logger.critical(f"Firebase initialization error: {e}")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"Unexpected error during Firebase initialization: {e}")
            sys.exit(1)
    
    def get_firestore(self) -> firestore.Client:
        """Get Firestore client with validation."""
        if self.db is None:
            raise RuntimeError("Firestore client not initialized")
        return self.db
    
    def close(self) -> None:
        """Cleanup Firebase resources."""
        try:
            if self.app:
                firebase_admin.delete_app(self.app)
                logger.info("Firebase app cleaned up")
        except Exception as e:
            logger.error(f"Error during Firebase cleanup: {e}")

# Global Firebase manager instance
firebase_manager = FirebaseManager()

def get_firestore() -> firestore.Client:
    """Helper function to get Firestore client."""
    return firebase_manager.get_firestore()

def close_firebase() -> None:
    """Helper function to close Firebase connections."""
    firebase_manager.close()

# Export for module usage
__all__ = ['firebase_manager', 'get_firestore', 'close_firebase']