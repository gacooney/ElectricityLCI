import pandas as pd
import numpy as np
import os
import sys
import warnings
warnings.filterwarnings("ignore")

from electricitylci.egrid_facilities import egrid_facilities
from electricitylci.egrid_emissions_and_waste_by_facility import years_in_emissions_and_wastes_by_facility
from electricitylci.globals import egrid_year
from electricitylci.eia923_generation import eia_download_extract
from electricitylci.generation_processes_from_egrid import emissions_and_waste_by_facility_for_selected_egrid_facilities




        
       
        
data_dir = os.path.dirname(os.path.realpath(__file__))+"\\data\\"
os.chdir(data_dir)  


#Reading the fuel name file
fuel_name = pd.read_excel('eLCI_data.xlsx', sheet_name='fuelname')

#Set aside the egrid emissions because these are not filtered
egrid_emissions_for_selected_egrid_facilities = emissions_and_waste_by_facility_for_selected_egrid_facilities[emissions_and_waste_by_facility_for_selected_egrid_facilities['Source'] == 'eGRID']

#Set aside the other emissions sources
non_egrid_emissions_for_selected_egrid_facilities = emissions_and_waste_by_facility_for_selected_egrid_facilities[emissions_and_waste_by_facility_for_selected_egrid_facilities['Source'] != 'eGRID']

#print(list(egrid_emissions_for_selected_egrid_facilities.columns.get_values()))
#['FacilityID', 'FlowAmount', 'FlowName', 'Compartment', 'ReliabilityScore', 'Source', 'Year', 'FRS_ID', 'eGRID_ID', 'FlowID', 'SRS_CAS', 'SRS_ID', 'Waste Code Type']

#Correcting eGRID ID to numeric type for better merging and code stability
emissions_and_waste_by_facility_for_selected_egrid_facilities['eGRID_ID'] = emissions_and_waste_by_facility_for_selected_egrid_facilities['eGRID_ID'].apply(pd.to_numeric,errors = 'coerce')


#pivoting the database from a list format to a table format
egrid_emissions_for_selected_egrid_facilities_pivot = pd.pivot_table(egrid_emissions_for_selected_egrid_facilities,index = ['FacilityID', 'FRS_ID','eGRID_ID','Year','Source','ReliabilityScore'] ,columns = 'FlowName', values = 'FlowAmount').reset_index()
emissions_for_selected_egrid_facilities_pivot = pd.pivot_table(emissions_and_waste_by_facility_for_selected_egrid_facilities,index = ['eGRID_ID','Year','Source','ReliabilityScore','Compartment'] ,columns = 'FlowName', values = 'FlowAmount').reset_index()
emissions_for_selected_egrid_facilities_pivot =  emissions_for_selected_egrid_facilities_pivot.drop_duplicates()


#Getting the electricity column for all flows
electricity_for_selected_egrid_facilities_pivot = pd.pivot_table(emissions_and_waste_by_facility_for_selected_egrid_facilities,index = ['eGRID_ID'] ,columns = 'FlowName', values = 'FlowAmount').reset_index()
electricity_for_selected_egrid_facilities_pivot = electricity_for_selected_egrid_facilities_pivot.drop_duplicates()
electricity_for_selected_egrid_facilities_pivot = electricity_for_selected_egrid_facilities_pivot[['eGRID_ID','Electricity']]
electricity_for_selected_egrid_facilities_pivot[['eGRID_ID_1','Electricity_1']] = electricity_for_selected_egrid_facilities_pivot[['eGRID_ID','Electricity']]
electricity_for_selected_egrid_facilities_pivot=electricity_for_selected_egrid_facilities_pivot.drop(columns = ['eGRID_ID','Electricity'])  

#merging main database with the electricity/net generation columns
emissions_for_selected_egrid_facilities_final = emissions_for_selected_egrid_facilities_pivot.merge(electricity_for_selected_egrid_facilities_pivot,left_on=['eGRID_ID'],right_on = ['eGRID_ID_1'],how='left')

#Finalizing the database
emissions_for_selected_egrid_facilities_final[['Electricity']] = emissions_for_selected_egrid_facilities_final[['Electricity_1']] 
emissions_for_selected_egrid_facilities_final  = emissions_for_selected_egrid_facilities_final.drop(columns = ['Electricity_1','eGRID_ID_1'])



#Checking the odd year
for year in years_in_emissions_and_wastes_by_facility:
    
    if year != egrid_year:
       odd_year = year;
       
   
#checking if any of the years are odd. If yes, we need EIA data. 
non_egrid_emissions_odd_year = emissions_for_selected_egrid_facilities_final[emissions_for_selected_egrid_facilities_final['Year'] == odd_year]
odd_database = pd.unique(non_egrid_emissions_odd_year['Source'])

#Downloading the required EIA923 data
if odd_year != None:
    EIA_923_gen_data = eia_download_extract(odd_year)


EIA_923_gen_data['Plant Id'] = EIA_923_gen_data['Plant Id'].apply(pd.to_numeric,errors = 'coerce')

#Merging database with EIA 923 data
database_with_new_generation = emissions_for_selected_egrid_facilities_final.merge(EIA_923_gen_data, left_on = ['eGRID_ID'],right_on = ['Plant Id'],how = 'left')



database_with_new_generation['Year'] = database_with_new_generation['Year'].apply(pd.to_numeric,errors = 'coerce')

database_with_new_generation = database_with_new_generation.sort_values(by = ['Year'])


#Replacing the odd year Net generations with the EIA net generations. 
database_with_new_generation['Electricity']= np.where(database_with_new_generation['Year'] == int(odd_year), database_with_new_generation['Net Generation\r\n(Megawatthours)'],database_with_new_generation['Electricity'])


#Dropping unnecessary columns
emissions_corrected_gen = database_with_new_generation.drop(columns = ['Plant Id','Plant Name','Plant State','YEAR','Net Generation\r\n(Megawatthours)','Total Fuel Consumption\r\nMMBtu'])

#return emissions_corrected_gen, None
#non_egrid_emissions_for_selected_egrid_facilities_pivot = emissions_corrected_gen[emissions_corrected_gen['Source'] != 'eGRID']

#Choosing only those columns needed
egrid_facilities = egrid_facilities[['FacilityID','Subregion','PrimaryFuel','FuelCategory']]
egrid_facilities[['FacilityID']] = egrid_facilities[['FacilityID']].apply(pd.to_numeric,errors = 'coerce')
emissions_corrected_gen[['eGRID_ID']] = emissions_corrected_gen[['eGRID_ID']].apply(pd.to_numeric,errors = 'coerce')


#Merging with the egrid_facilites file to get the subregion information in the database!!!
emissions_corrected_final_data = egrid_facilities.merge(emissions_corrected_gen, left_on = ['FacilityID'], right_on = ['eGRID_ID'], how = 'right')

emissions_corrected_final_data  = emissions_corrected_final_data.sort_values(by = ['FacilityID'])