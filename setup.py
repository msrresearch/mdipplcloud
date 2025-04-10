from setuptools import setup, find_packages

setup(
    name='mdipplcloud',
    version='0.2',
    packages=find_packages(),
    install_requires=[
        'requests',
    ],
    url='https://github.com/msrresearch/mdipplcloud',
    license='MIT',
    author='Martin Schulte-Rüther',
    author_email='martin@schulte-ruether.de',
    description='Pupil Labs Cloud API Wrapper'
)


