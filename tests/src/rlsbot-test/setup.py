try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='rlsbot-test',
    version='1.0.0',
    py_modules=['rlsbot_test'],
    python_requires='>=2',
    url='https://github.com/user-cont/release-bot/',
    license='GPLv3+',
    author='Red Hat',
    author_email='user-cont@redhat.com',
    description='This is a test package',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3'
    ],
    entry_points={'console_scripts': [
        'rlsbot-test=rlsbot_test:main',
    ]}
)
