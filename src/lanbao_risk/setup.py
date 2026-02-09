from setuptools import setup

package_name = 'lanbao_risk'

setup(
    name=package_name,
    version='0.5.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='揽宝开发团队',
    maintainer_email='dev@lanbao.com',
    description='揽宝风险控制服务',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'risk_control_node = lanbao_risk.risk_control_node:main',
        ],
    },
)
