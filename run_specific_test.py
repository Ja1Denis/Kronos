import unittest
import sys
import os

# Add root directory to path
sys.path.append(os.getcwd())

# Load tests
loader = unittest.TestLoader()
suite = loader.discover('tests', pattern='test_api_jobs.py')

# Run tests
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

if not result.wasSuccessful():
    sys.exit(1)
