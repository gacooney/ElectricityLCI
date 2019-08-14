# -*- coding: utf-8 -*-
"""
Created on Fri Aug  2 13:39:57 2019

@author: cooneyg
"""

from electricitylci import eia923_generation


df = eia923_generation.eia923_boiler_fuel(2016)

df = eia923_generation.eia923_generation_and_fuel(2016)
