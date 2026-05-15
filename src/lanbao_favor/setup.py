from setuptools import setup

package_name = 'lanbao_favor'

setup(
    name=package_name,
    version='0.5.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='揽宝开发团队',
    maintainer_email='dev@lanbao.com',
    description='揽宝自选股管理模块',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'favor_node = lanbao_favor.favor_node:main',
        ],
    },
)
