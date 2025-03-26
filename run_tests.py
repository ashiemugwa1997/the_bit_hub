#!/usr/bin/env python
import os
import sys
import django
import coverage
import argparse

def run_tests_with_coverage():
    """Run tests with coverage reporting"""
    parser = argparse.ArgumentParser(description='Run Django tests with coverage reporting.')
    parser.add_argument('--module', help='Specific module to test (e.g., models, views)')
    parser.add_argument('--html', action='store_true', help='Generate HTML coverage report')
    args = parser.parse_args()
    
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_bit_hub_project.settings')
    django.setup()
    
    # Start coverage
    cov = coverage.Coverage(
        source=['trading_hub'],
        omit=[
            '*/migrations/*',
            '*/tests/*',
            '*/apps.py',
            '*/admin.py',
            '*/management/commands/*',
            '*/templatetags/*',
            '*/wsgi.py',
            '*/asgi.py',
        ]
    )
    cov.start()
    
    # Run tests
    from django.test.utils import get_runner
    TestRunner = get_runner(django.conf.settings)
    test_runner = TestRunner(verbosity=2)
    
    if args.module:
        test_label = f'trading_hub.tests.test_{args.module}'
        print(f"Running tests for module: {args.module}")
        failures = test_runner.run_tests([test_label])
    else:
        failures = test_runner.run_tests(['trading_hub.tests'])
    
    # End coverage
    cov.stop()
    cov.save()
    
    # Report coverage
    print("\nCoverage report:")
    cov.report()
    
    # Generate HTML report if requested
    if args.html:
        htmlcov_dir = os.path.join(os.path.dirname(__file__), 'htmlcov')
        print(f"\nGenerating HTML coverage report in {htmlcov_dir}")
        cov.html_report(directory=htmlcov_dir)
    
    sys.exit(bool(failures))

if __name__ == '__main__':
    run_tests_with_coverage()
