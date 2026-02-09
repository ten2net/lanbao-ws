from setuptools import setup

package_name = 'lanbao_backtest'

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
    description='揽宝回测引擎 - DuckDB向量化回测',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'backtest_engine_node = lanbao_backtest.backtest_engine_node:main',
        ],
    },
)
