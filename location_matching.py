#####
# Title: location_matching.py
# Author: Mahkah Wu
# 
# Description:
# Match police reported locations of stop and frisks to the DC Government's 
# block dataset to find longitude and latitude values for each incident. 
# Currently matches 92% of incidents (>30,000 in total). Of the remaining 
# incidents, >70% have missing or incomplete addresses.
#
# Modified: 4/7/2018 (Export Format Updates)
# 3/21/2018 (Initial Version)
#####

### Missing Blocks
# 400 BLOCK OF 2ND STREET NW: (38.895470, -77.013673)



import numpy as np
import pandas as pd
import re
import json



def main():
    '''Run the functions defined in this file on DC Stop and Frisk Data'''
    # Read Data
    # From: https://mpdc.dc.gov/node/1310236
    sf1_df = pd.read_excel('SF_Field Contact_02202018.xlsx', 
                           names=('incident_type', 'incident_date', 'year', 'data_type', 
                                  'subject_race', 'subject_gender', 'subject_ethnicity', 
                                  'block_address', 'district', 'psa', 'subject_age'))
    
    sf2_df = pd.read_excel('SF_Field Contact_02202018.xlsx', sheet_name=1,
                           names=('incident_date', 'year', 'block_address', 'district', 
                                  'psa', 'incident_type', 'cause', 'data_type', 
                                  'subject_race', 'subject_ethnicity', 
                                  'subject_gender', 'subject_age'))
    
    # From: http://opendata.dc.gov/datasets/block-centroids/data
    block_df = pd.read_excel('Block_Centroids.xlsx')
    block_df.set_index('PSEUDO_OBJECTID', inplace=True, drop=False)
    
    
    # Geocode Incidents
    sf1_df = find_blocks(sf1_df, 'block_address', block_df, details=True)
    sf2_df = find_blocks(sf2_df, 'block_address', block_df, details=True)
    sf_located = sf1_df.append(sf2_df, ignore_index=True)
    
    match_codes = {1: 'Matched', -1: 'Address Missing', -2: "Address listed as 'Multiple/Unknown Address'", 
                   -3: 'Unmatchable block', -4: 'Unmatchable corner',  -5: 'Other unmatchable address'}
    sf_located['block_match'] = sf_located['block_match'].map(match_codes)
    print(sf_located['block_match'].value_counts(normalize=True))
    
    
    # Recoding
    sf_located['subject_race_ethn'] = sf_located['subject_race']
    sf_located.loc[sf_located['subject_ethnicity'] == 'Hispanic Or Latino', 'subject_race_ethn'] = 'Hispanic or Latino'
    recode_dict = {'Asian': 'Other', 'American Indian Or Alaska Native': 'Other', 'Native Hawaiian Or Other Pacific Islander': 'Other'}
    sf_located['subject_race_ethn'].replace(recode_dict, inplace=True)
    
    sf_located['incident_date'] = pd.to_datetime(sf_located['incident_date'])
    sf_located['month'] = sf_located['incident_date'].dt.month
    sf_located['day'] = sf_located['incident_date'].dt.day
    sf_located['hour'] = sf_located['incident_date'].dt.hour
    
    cols = list(sf_located)
    cols.remove('X')
    cols.remove('Y')
    cols.remove('incident_date')
    for col in cols:
        sf_located[col] = sf_located[col].replace(np.nan, 'Unknown', regex=True)
        sf_located[col] = sf_located[col].replace('', 'Unknown', regex=True)
    
    
    # Export
    sf_located.to_csv('SF_Field Contact_02202018_locations.csv', index=False)
    
    geo_df = sf_located.loc[sf_located['block_id'] > 0]

    geojson = df_to_geojson(geo_df, cols, lat='Y', lon='X') 
    output_filename = 'SF_Field_Contact_02202018_locations.geojson'
    with open(output_filename, 'w') as output_file:
        output_file.write('')
        json.dump(geojson, output_file, indent=2)



def spell_check(address):
    '''Conduct basic spell checking'''
    spelling_counts = {'CAPTIOL': 'CAPITOL', 'CAPITAL': 'CAPITOL', 'ILINOI': 'ILLINOIS',
                   '/ SCAPITOL': 'SOUTH CAPITOL', "13'TH": '13TH', 'EAST CAP ST': 'EAST CAPITOL ST',
                   'E CAPITOL': 'EAST CAPITOL', 'MLK JR': 'MARTIN LUTHER KING JR', 
                   'CAPITOL / 295N': 'CAPITOL STREET', 'MLKJR': 'MARTIN LUTHER KING JR',
                   'MT PLEASANT': 'MOUNT PLEASANT', 'MARTIN LUTHER KING AV': 'MARTIN LUTHER KING JR AV',
                   'MLK AV': 'MARTIN LUTHER KING JR AV', '4ST': '4TH STREET', '7TH T': '7TH STREET', 
                   'V STNW': 'V ST NW', 'N CAPITOL ST': 'NORTH CAPITOL ST', 'RI AV': 'RHODE ISLAND AV',
                   'N / W': 'NW', 'GA AV': 'GEORGIA AV', 'MD AV': 'MARYLAND AV',
                   'AVENW': 'AVE NW', 'PA AV': 'PENNSYLVANIA AV', 'STNW': 'ST NW', 
                   'NORTH CAPITOL NE': 'NORTH CAPITOL STREET', '19THST': '19TH STREET',
                   '7TH T': '7TH STREET', 'NEW YORK AVENE NE': 'NEW YORK AVENUE NE',
                   'ST;NW': 'ST NW', '13 TH': '13TH', 'N CAP ST': 'NORTH CAPITOL ST', 
                   'ECAPITAL ST': 'EAST CAPITOL ST', 'BLK OF': 'BLOCK OF', 'BLK': 'BLOCK OF'}
    for k, v in spelling_counts.items():
        m = re.match('^(.* )' + k + '(.*)$', address)
        if m:
            address = m.group(1) + v + m.group(2)
    return address



def fix_ending(address):
    '''Remove endings like " WASHINGTON DC"'''
    if 'CAPITOL' not in address:
        m = re.match('^.* [NS][EW]$', address)
        if m is None:
            m = re.match('^(.* [NS][EW]) .*$', address)
            if m is not None:
                return m.group(1)
    return address



def street_abriev(address):
    '''Standardize data to use full st type names'''
    abrievs = {'ALY': 'ALLEY',
           'AVE': 'AVENUE',
           'AV': 'AVENUE',
           'BLVD': 'BOULEVARD',
           'BRG': 'BRIDGE',
           'CIR': 'CIRCLE',
           'CT': 'COURT',
           'CRES': 'CRESCENT',
           'DR': 'DRIVE',
           'EXPY': 'EXPRESSWAY',
           'FWY': 'FREEWAY',
           'GDN': 'GARDENS',
           'GDNS': 'GARDENS',
           'GRN': 'GREEN',
           'KYS': 'KEYS',
           'LN': 'LANE',
           'LOOP': 'LOOP',
           'MEWS': 'MEWS',
           'PKWY': 'PARKWAY',
           'PL': 'PLACE',
           'PLZ': 'PLAZA',
           'RD': 'ROAD',
           'ROW': 'ROW',
           'SQ': 'SQUARE',
           'ST': 'STREET',
           'TER': 'TERRACE',
           'TR': 'TERRACE',
           'WALK': 'WALK',
           'WAY': 'WAY'}
    for k, v in abrievs.items():
        m = re.match('^(.* )' + k + '( ?[SN]?[WE]?)$', address)
        if m:
            return m.group(1) + v + m.group(2)
    return address



def internal_street_abriev(address):
    '''Standardize corner addresses to use full st type names'''
    abrievs = {'ALY': 'ALLEY',
           'AVE': 'AVENUE',
           'AV': 'AVENUE',
           'BLVD': 'BOULEVARD',
           'BRG': 'BRIDGE',
           'CIR': 'CIRCLE',
           'CT': 'COURT',
           'CRES': 'CRESCENT',
           'DR': 'DRIVE',
           'EXPY': 'EXPRESSWAY',
           'FWY': 'FREEWAY',
           'GDN': 'GARDENS',
           'GDNS': 'GARDENS',
           'GRN': 'GREEN',
           'KYS': 'KEYS',
           'LN': 'LANE',
           'LOOP': 'LOOP',
           'MEWS': 'MEWS',
           'PKWY': 'PARKWAY',
           'PL': 'PLACE',
           'PLZ': 'PLAZA',
           'RD': 'ROAD',
           'ROW': 'ROW',
           'SQ': 'SQUARE',
           'ST': 'STREET',
           'TER': 'TERRACE',
           'TR': 'TERRACE',
           'WALK': 'WALK',
           'WAY': 'WAY'}
    if re.match('^(.*) [&/] (.*)$', address):
       for k, v in abrievs.items():
           m = re.match('^(.* )' + k + '( ?[SN]?[WE]? [&/] .+)$', address)
           if m:
               return m.group(1) + v + m.group(2)
    return address 



def clean_address(address):
    '''Clean up special cases'''
    
    ### Deletions
    deletions = ['(.* [0-9]TH)S( .*)$', '(.*)\.( [NS][WE])$', '(.* BLOCK OF) .* [NS][WE] /( .*[NS][WE])$', 
             '(.* BLOCK OF )OF (.*[NS][WE])$', '(.* BLOCK OF )BLOCK OF (.*[NS][WE])$', 
             '(.* BLOCK OF )BLK OF (.*[NS][WE])$', '(.* BLOCK OF )BLOCK (.*[NS][WE])$']
    for i in deletions:
        m = re.match(i, address)
        if m: 
            address = m.group(1) + m.group(2)
    
    ### North/South/East Capitol Street - The Snowflake Street
    # The boundary streets shouldn't have quadrants
    if re.match('(.* CAPITOL ST)$', address):
        address = re.match('(.* CAPITOL ST)$', address).group(1) + 'REET'
    if re.match('(.* CAPITOL STREET) [NS][WE]$', address):
        address = re.match('(.* CAPITOL STREET) [NS][WE]$', address).group(1)
    
    ### Numbered Streets
    # Fixing numbered streets that lack their suffix (e.g. 1 -> 1ST)
    if re.match('(.* BLOCK OF 1)( ST.*)$', address):
        m = re.match('(.* BLOCK OF 1)( ST.*)$', address)
        address = m.group(1) + 'ST' + m.group(2)
    elif re.match('(.* BLOCK OF 2)( ST.*)$', address):
        m = re.match('(.* BLOCK OF 2)( ST.*)$', address)
        address = m.group(1) + 'ND' + m.group(2)
    elif re.match('(.* BLOCK OF 3)( ST.*)$', address):
        m = re.match('(.* BLOCK OF 3)( ST.*)$', address)
        address = m.group(1) + 'RD' + m.group(2)
    elif re.match('(.* BLOCK OF [4-9])( ST.*)$', address):
        m = re.match('(.* BLOCK OF [4-9])( ST.*)$', address)
        address = m.group(1) + 'TH' + m.group(2)
    elif re.match('(.* BLOCK OF [1-9][0-9])( ST.*)$', address):
        m = re.match('(.* BLOCK OF [1-9][0-9])( ST.*)$', address)
        address = m.group(1) + 'TH' + m.group(2)
    # Fixing our tendency to say '1st and such and such street'
    if re.match('([0-9]{1,2}[SNRT][TDH])( ?[NS]?[EW]? [&/] .*)', address):
        m = re.match('([0-9]{1,2}[SNRT][TDH])( ?[NS]?[EW]? [&/] .*)', address)
        address = m.group(1) + ' STREET' + m.group(2)
    if re.match('(.*[0-9]{1,2}[SNRT][TDH])( [NS][EW]$)', address):
        m = re.match('(.*[0-9]{1,2}[SNRT][TDH])( [NS][EW]$)', address)
        address = m.group(1) + ' STREET' + m.group(2)
    
    ### Quadrants for corners
    # Check to make sure quandrant is labled for both streets 
    # (as long as they aren't North/South/East Capitol or other special cases)
    m = re.match('^(.*) [&/] (.*)$', address)
    if m:
        if (' CAPITOL ' not in m.group(1)) and (' CAPITOL ' not in m.group(2)):
            quad1 = ''
            quad2 = ''
            if re.match('.*( [NS][EW])', m.group(1)) is not None:
                quad1 = re.match('.*( [NS][EW])', m.group(1)).group(1)
            if re.match('.*( [NS][EW])', m.group(2)) is not None:
                quad2 = re.match('.*( [NS][EW])', m.group(2)).group(1)
            if quad1 == '' and quad2 != '':
                address = m.group(1) + quad2 + ' & ' + m.group(2)
            elif quad1 != '' and quad2 == '':
                address = m.group(1) + ' & ' + m.group(2) + quad1
    
    ### Unit Blocks
    m = re.match('^UNIT (BLOCK OF.*)$', address)
    if m:
        address = '0 ' + m.group(1)
    
    ### Spot Fixes
    # Fixing Benning Road SE Block
    if address == '4500 BLOCK OF BENNING ROAD SE':
        address = '4510 BLOCK OF BENNING ROAD SE'
    # Fixing Howard Rd outside Anacostia Metro
    elif address == '1100 BLOCK OF HOWARD ROAD SE':
        address = '1007 BLOCK OF HOWARD ROAD SE'
    # Fixing Cedar St near Frederick Douglass House
    elif address == '1400 BLOCK OF CEDAR STREET SE':
        address = '1424 BLOCK OF CEDAR STREET SE'
    # Fixing Water St near Capitol Crescent Trailhead
    elif address == '4400 BLOCK OF WATER STREET NW':
        address = '3599 BLOCK OF WATER STREET NW'
    # Fixing Douglass Place SE - Lots of streets named for Frederick Douglass
    elif address == '2700 BLOCK OF DOUGLASS PLACE SE':
        address = '2657 BLOCK OF DOUGLASS PLACE SE'
    return address



def block_finder(address, block_df):
    '''Find the pseudo block id of each block. Negative numbers designate 
    various match failures
    '''
    if address == '' or address=='nan':
        return -1
    if address == 'Multiple/Unknown Address':
        return -2
    
    # Block of address type
    m = re.match('^([0-9]+) BLOCK OF (.*)$', address)
    if m:
        st_num = int(m.group(1))
        block_id = block_df.loc[(block_df['ONSTREETDISPLAY'] == m.group(2)) & 
                                     (block_df['LOWER_RANGE'] <= st_num) & 
                                     (block_df['HIGHER_RANGE'] >= st_num), 
                                     'PSEUDO_OBJECTID'].values
        if len(block_id) > 0:
            return block_id[0]
        # Try making street number fuzzy
        st_num = st_num + 5
        block_id = block_df.loc[(block_df['ONSTREETDISPLAY'] == m.group(2)) & 
                                 (block_df['LOWER_RANGE'] <= st_num) & 
                                 (block_df['HIGHER_RANGE'] >= st_num), 
                                 'PSEUDO_OBJECTID'].values
        if len(block_id) > 0:
            return block_id[0]
        st_num = st_num - 10
        block_id = block_df.loc[(block_df['ONSTREETDISPLAY'] == m.group(2)) & 
                                 (block_df['LOWER_RANGE'] <= st_num) & 
                                 (block_df['HIGHER_RANGE'] >= st_num), 
                                 'PSEUDO_OBJECTID'].values
        if len(block_id) > 0:
            return block_id[0]
        return -3
    
    # Corner address type
    m = re.match('^(.*) [&/] (.*)$', address)
    if m:
        block_id = block_df.loc[
                ((block_df['ONSTREETDISPLAY'] == m.group(1)) & (block_df['FROMSTREETDISPLAY'] == m.group(2))) | 
                ((block_df['ONSTREETDISPLAY'] == m.group(2)) & (block_df['FROMSTREETDISPLAY'] == m.group(1))) |
                ((block_df['ONSTREETDISPLAY'] == m.group(1)) & (block_df['TOSTREETDISPLAY'] == m.group(2))) |
                ((block_df['ONSTREETDISPLAY'] == m.group(2)) & (block_df['TOSTREETDISPLAY'] == m.group(1))), 
                'PSEUDO_OBJECTID'].values
        if len(block_id) > 0:
            return block_id[0]
        else:
            return -4
    return -5



def find_blocks(df_sf, addres_col, block_df, details=False):
    '''Run clean up and matching functions, assess match, and get useful 
    columns from the block dataset
    '''
    ### Clean up and find block id's
    df = df_sf
    df['ba_clean'] = df[addres_col].str.replace(' B/O ', ' BLOCK OF ')
    df['ba_clean'] = df['ba_clean'].apply(str).apply(spell_check)
    df['ba_clean'] = df['ba_clean'].apply(fix_ending)
    df['ba_clean'] = df['ba_clean'].apply(street_abriev)
    df['ba_clean'] = df['ba_clean'].apply(internal_street_abriev)
    df['ba_clean'] = df['ba_clean'].apply(clean_address)
    df['block_id'] = df['ba_clean'].apply(block_finder, block_df=block_df)
    df['block_match'] = df['block_id']
    df.loc[df['block_match'] > 0, 'block_match'] = 1
    df['original_index'] = df.index
    
    ### Match Assessment
    # BLOCK OF Pattern
    if details == True:
        print(df.loc[df['block_id']==-3, 'ba_clean'].value_counts())
    unclassified_bo = len(df.loc[df['block_id']==-3, addres_col])
    total_bo = df[addres_col].str.count('^([0-9]+) BLOCK OF (.*)$').sum() + df[addres_col].str.count('^([0-9]+) B/O (.*)$').sum()
    print('Block of pattern: ' + str((total_bo-unclassified_bo)/total_bo))
    
    # CORNER Pattern
    if details == True:
        print(df.loc[df['block_id']==-4, 'ba_clean'].value_counts())
    unclassified_bo = len(df.loc[df['block_id']==-4, addres_col])
    total_bo = df[addres_col].str.count('^(.*) [/&] (.*)$').sum()
    print('Corner pattern: ' + str((total_bo-unclassified_bo)/total_bo))
    
    # Other Pattern
    if details == True:
        print(df.loc[df['block_id']==-5, 'ba_clean'].value_counts())
    
    ### Join with block data
    return df.join(block_df[['X', 'Y']], on='block_id')



def df_to_geojson(df, properties, lat='latitude', lon='longitude'):
    '''Write a dataframe to a geojson format
    Retrieved from Geoff Boeing: http://geoffboeing.com/2015/10/exporting-python-data-geojson/
    '''
    geojson = {'type':'FeatureCollection', 'features':[]}
    for _, row in df.iterrows():
        feature = {'type':'Feature',
                   'properties':{},
                   'geometry':{'type':'Point',
                               'coordinates':[]}}
        feature['geometry']['coordinates'] = [row[lon],row[lat]]
        for prop in properties:
            feature['properties'][prop] = row[prop]
        geojson['features'].append(feature)
    return geojson


if __name__ == '__main__': main()
