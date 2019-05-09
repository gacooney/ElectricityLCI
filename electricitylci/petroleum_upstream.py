# -*- coding: utf-8 -*-
import pandas as pd
from electricitylci.coal_upstream import read_eia923_fuel_receipts
from os.path import join
from electricitylci.globals import data_dir, output_dir
import electricitylci.PhysicalQuantities as pq

def generate_petroleum_upstream(year):
    """
    Generate the annual petroleum extraction, transport, and refining emissions
    (in kg) for each plant in EIA923.
    
    Parameters
    ----------
    None
    
    Returns
    ----------
    dataframe
    """
    eia_fuel_receipts_df=read_eia923_fuel_receipts(year)
    petroleum_criteria = eia_fuel_receipts_df['fuel_group']=='Petroleum'
    eia_fuel_receipts_df=eia_fuel_receipts_df.loc[petroleum_criteria,:]
    
    eia_fuel_receipts_df['heat_input']=(
            eia_fuel_receipts_df['quantity']*
            eia_fuel_receipts_df['average_heat_content']*
            pq.convert(10**6,'Btu','MJ'))
    
    #Sum all fuel use by plant, plant state, and DFO/RFO
    eia_fuel_receipts_df=eia_fuel_receipts_df.groupby(
            ['plant_id','plant_state','energy_source'],
            as_index=False)['heat_input'].sum()
    
    #Assume that plants have fuel delivered from the PADD they are in. Note
    #that the crude represented in each PADD is the mix of crude going into
    #that PADD, domestically-produced and imported, and the refining emissions
    #are representative of the mix of refinery types in that PADD.
    state_padd_df=pd.read_csv(data_dir+'/state_padd.csv')
    state_padd_dict=pd.Series(
            state_padd_df.padd.values,index=state_padd_df.state).to_dict()
    
    #Assign each power plant to a PADD.
    eia_fuel_receipts_df['padd']=(
            eia_fuel_receipts_df['plant_state'].map(state_padd_dict))
    
    #Creating a dictionary to store the inventories of each fuel/PADD
    #combination
    petroleum_lci={}
    fuels=['Diesel','Bunker']
    fuels_map={'Diesel':'DFO',
               'Bunker':'RFO'
            }
    padds=[1,2,3,4,5]
    expected_lci_folder = 'petroleum_inventory'
    for fuel in fuels:
        for padd in padds:
            fn = f'PRELIM_Mixer__{fuel}___PADD_{padd}_.xlsx'
            path = join(data_dir,expected_lci_folder,fn)
            key = f'{fuels_map[fuel]}_{padd}'
            petroleum_lci[key]=pd.read_excel(
                    path,
                    sheet_name='Inventory',
                    usecols="I:N",
                    skiprows=2)
            petroleum_lci[key]['fuel_code']=f'{fuels_map[fuel]}_{padd}'
    
    #Merging the dataframes within the dictionary to a single datframe
    combined_lci=pd.concat(petroleum_lci,ignore_index=True)
    eia_fuel_receipts_df['fuel_padd']=(eia_fuel_receipts_df['energy_source']+'_'+eia_fuel_receipts_df['padd'].astype(str))
    
    #Merge the inventories for each fuel with the fuel use by each power plant
    merged_inventory = combined_lci.merge(right=eia_fuel_receipts_df[['plant_id','heat_input','fuel_padd']],
                                          left_on='fuel_code',
                                          right_on='fuel_padd',
                                          how='left').sort_values(['plant_id','fuel_padd','Flow.1'])
    
    #convert per MJ inventory to annual emissions using plant heat input
    merged_inventory['Result.1']=merged_inventory['Result.1']*merged_inventory['heat_input']
    
    #Cleaning up unneeded columns and renaming
    merged_inventory.drop(columns=['heat_input','fuel_padd','Unit.1','Sub-category.1','Flow UUID.1'],inplace=True)
    colnames={
            'Flow.1':'FlowName',
            'Category.1':'Compartment',
            'Result.1':'FlowAmount',
            'fuel_code':'stage_code'}
    merged_inventory.rename(columns=colnames,inplace=True)
    merged_inventory['fuel_type']='Petroleum'
    merged_inventory['stage']='well-to-tank'
    merged_inventory.reset_index(inplace=True,drop=True)
    
    #Change compartment values to be standard'
    compartment_dict={
            'Emission to air':'air',
            'NETL database':'NETL',
            'Emission to water':'water',
            'Emission to soil':'soil'}
    merged_inventory['Compartment']=merged_inventory['Compartment'].map(compartment_dict)
    merged_inventory.dropna(inplace=True)
    
    return merged_inventory

if __name__=='__main__':
    year=2016
    df=generate_petroleum_upstream(year)
    df.to_csv(output_dir+'/petroleum_emissions_{}.csv'.format(year))
    