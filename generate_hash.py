#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.security import hash_password

# Generate hash for "admin123"
password = "admin123"
hashed = hash_password(password)
print(f"Password: {password}")
print(f"Hash: {hashed}")
