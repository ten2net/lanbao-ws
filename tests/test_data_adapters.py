"""
数据源适配器测试
"""
import sys
sys.path.insert(0, '../src')

import unittest
from unittest.mock import Mock, patch
import pandas as pd


class TestTushareAdapter(unittest.TestCase):
    """测试Tushare适配器"""
    
    def test_priority(self):
        """测试优先级设置"""
        from lanbao_data import TushareAdapter
        
        # Mock环境变量
        with patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            with patch('lanbao_data.tushare_adapter.ts.pro_api'):
                adapter = TushareAdapter()
                self.assertEqual(adapter.priority, 1)


class TestTDXAdapter(unittest.TestCase):
    """测试通达信适配器"""
    
    def test_priority(self):
        """测试优先级设置"""
        from lanbao_data import TDXAdapter
        
        with patch('lanbao_data.tdx_adapter.TdxHq_API'):
            adapter = TDXAdapter()
            self.assertEqual(adapter.priority, 2)
    
    def test_convert_symbol(self):
        """测试代码转换"""
        from lanbao_data import TDXAdapter
        
        with patch('lanbao_data.tdx_adapter.TdxHq_API'):
            adapter = TDXAdapter()
            
            # 测试深交所代码
            self.assertEqual(adapter._get_market_code('000001.SZ'), 0)
            self.assertEqual(adapter._get_market_code('000001'), 0)
            
            # 测试上交所代码
            self.assertEqual(adapter._get_market_code('600000.SH'), 1)
            self.assertEqual(adapter._get_market_code('600000'), 1)
            
            # 测试转换
            self.assertEqual(adapter._convert_symbol('000001.SZ'), '000001')
            self.assertEqual(adapter._convert_symbol('000001'), '000001')


class TestAKShareAdapter(unittest.TestCase):
    """测试AkShare适配器"""
    
    def test_priority(self):
        """测试优先级设置"""
        from lanbao_data import AKShareAdapter
        
        with patch('lanbao_data.akshare_adapter.ak'):
            adapter = AKShareAdapter()
            self.assertEqual(adapter.priority, 3)
    
    def test_convert_symbol(self):
        """测试代码转换"""
        from lanbao_data import AKShareAdapter
        
        with patch('lanbao_data.akshare_adapter.ak'):
            adapter = AKShareAdapter()
            
            # 测试深交所代码
            self.assertEqual(adapter._convert_symbol('000001.SZ'), 'sz000001')
            
            # 测试上交所代码
            self.assertEqual(adapter._convert_symbol('600000.SH'), 'sh600000')
            
            # 测试纯代码
            self.assertEqual(adapter._convert_symbol('000001'), 'sz000001')
            self.assertEqual(adapter._convert_symbol('600000'), 'sh600000')


class TestMiniQMTAdapter(unittest.TestCase):
    """测试MiniQMT适配器"""
    
    def test_priority(self):
        """测试优先级设置"""
        from lanbao_data import MiniQMTAdapter
        
        adapter = MiniQMTAdapter()
        self.assertEqual(adapter.priority, 1)
    
    def test_convert_symbol(self):
        """测试代码转换"""
        from lanbao_data import MiniQMTAdapter
        
        adapter = MiniQMTAdapter()
        
        # 测试深交所代码
        self.assertEqual(adapter._convert_symbol('000001.SZ'), '000001.SZ')
        
        # 测试上交所代码
        self.assertEqual(adapter._convert_symbol('600000.SH'), '600000.SH')
        
        # 测试纯代码 - 深交所
        self.assertEqual(adapter._convert_symbol('000001'), '000001.SZ')
        
        # 测试纯代码 - 上交所
        self.assertEqual(adapter._convert_symbol('600000'), '600000.SH')
        
        # 测试纯代码 - 北交所
        self.assertEqual(adapter._convert_symbol('430047'), '430047.BJ')


class TestMultiDataSource(unittest.TestCase):
    """测试多数据源功能"""
    
    def test_adapter_priority_order(self):
        """测试适配器优先级排序"""
        from lanbao_data import TushareAdapter, TDXAdapter, AKShareAdapter, MiniQMTAdapter
        
        # 创建mock适配器
        adapters = []
        
        # 测试优先级数值
        with patch.dict('os.environ', {'TUSHARE_TOKEN': 'test'}):
            with patch('lanbao_data.tushare_adapter.ts.pro_api'):
                tushare = TushareAdapter()
                adapters.append(('Tushare', tushare, tushare.priority))
        
        with patch('lanbao_data.tdx_adapter.TdxHq_API'):
            tdx = TDXAdapter()
            adapters.append(('TDX', tdx, tdx.priority))
        
        with patch('lanbao_data.akshare_adapter.ak'):
            akshare = AKShareAdapter()
            adapters.append(('AKShare', akshare, akshare.priority))
        
        miniqmt = MiniQMTAdapter()
        adapters.append(('MiniQMT', miniqmt, miniqmt.priority))
        
        # 按优先级排序
        sorted_adapters = sorted(adapters, key=lambda x: x[2])
        
        print("\n适配器优先级排序:")
        for name, _, priority in sorted_adapters:
            print(f"  {name}: {priority}")
        
        # 验证优先级顺序
        priorities = [p for _, _, p in sorted_adapters]
        self.assertEqual(priorities, sorted(priorities))


if __name__ == '__main__':
    unittest.main()
