from setuptools import setup, find_packages

setup(
    name="msemu",
    version="0.0.1",
    description='Mixed-signal emulation generator',
    url='https://github.com/sgherbst/msemu',
    author='Steven Herbst',
    author_email='sherbst@stanford.edu',
    packages=['msemu'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'numpy',
        'scipy',
        'matplotlib',
        'mpltools',
        'wget',
        'cvxpy',
        'scikit-rf'
    ]
)
