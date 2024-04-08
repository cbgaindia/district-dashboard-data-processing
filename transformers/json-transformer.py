import json
import math
import os
import re
import pandas as pd

CURRENT_FOLDER = os.path.realpath(os.path.join(__file__, '..'))

files_directory = os.path.join(CURRENT_FOLDER, 'state-wise')

merged_json_files_directory = os.path.join(CURRENT_FOLDER, 'state-wise-json')

os.makedirs(merged_json_files_directory, exist_ok=True)

def slugify(s):
    return re.sub('\s+', '-', s.strip().lower())


def convert_nan_values_to_na_string(val):
    return 'NA' if math.isnan(val) else val


def main():
    for file in os.listdir(files_directory):    
        filename = os.path.join(files_directory, file)

        print(filename)

        if os.path.isfile(filename):
            df = pd.read_csv(filename)
            
            # District Name Lookup Dictionary
            kf = df[['district_name', 'district_code_lg']].drop_duplicates('district_code_lg')
            district_name_lookup = dict(zip(kf.district_code_lg, kf.district_name))
            
            state_average_dict = {}

            kkf = df.drop(['district_name', 'district_code_lg'], axis=1).groupby(['fiscal_year','scheme_slug', 'indicator_name'])['indicator_value'].aggregate(['min', 'max', 'median']).reset_index()
            
            for i in list(kkf.values):            
                i[2] = slugify(i[2])

                state_average_values = {
                        'min': convert_nan_values_to_na_string(i[3]),
                        'max': convert_nan_values_to_na_string(i[4]),
                        'avg': convert_nan_values_to_na_string(i[5]),
                }
                
                if i[0] not in state_average_dict.keys():
                    state_average_dict[i[0]] = {i[1]: {i[2]: state_average_values}}
                    
                if i[1] not in state_average_dict[i[0]].keys():
                    state_average_dict[i[0]][i[1]] = {i[2]: state_average_values}
                    
                if i[2] not in state_average_dict[i[0]][i[1]].keys():
                    state_average_dict[i[0]][i[1]][i[2]] = state_average_values

            ddf = df.groupby(['district_code_lg','fiscal_year','scheme_slug','indicator_name','indicator_value']).groups
            
            shared_dict = {}
            
            for i in ddf:
                i = list(i)
                i[0] = int(i[0])
                i[3] = slugify(i[3])
                i[4] = convert_nan_values_to_na_string(i[4])
                
                if i[0] not in shared_dict.keys():
                    shared_dict[i[0]]={"district_code_lg":i[0], "district_name_name":district_name_lookup[i[0]], "fiscal_year":{i[1]:{i[2]:{i[3]:i[4]}}}}
                
                if i[1] not in shared_dict[i[0]]["fiscal_year"].keys():
                    shared_dict[i[0]]["fiscal_year"][i[1]] = {i[2]:{i[3]:i[4]}}
                if i[2] not in shared_dict[i[0]]["fiscal_year"][i[1]].keys():
                    shared_dict[i[0]]["fiscal_year"][i[1]][i[2]] = {i[3]:i[4]}
                else:
                    shared_dict[i[0]]["fiscal_year"][i[1]][i[2]][i[3]] = i[4]

            # Chage sequence of common indicators
            schemes_sequence = [
                'mgnrega', 'pmay', 'sbm_g', 'pmmvy', 'mdm', 'icds', 'pmfby_rabi', 'pmfby_kharif', 'pmkisan', 'nsap', 'nhm', 'smsa', 'sbm_u'
            ]

            for _ in state_average_dict:
                scheme_data = state_average_dict[_]
                state_average_dict[_] = {}

                for scheme in schemes_sequence:
                    if scheme not in scheme_data.keys():
                        continue

                    # Because CKAN names don't have `_` for these schemes
                    scheme_name = scheme
                    if scheme == 'sbm_g' or scheme == 'sbm_u':
                        scheme_name = scheme.replace('_', '')

                    state_average_dict[_].update({scheme_name: scheme_data[scheme]})

            for _ in shared_dict:
                for year in shared_dict[_]['fiscal_year']:
                    scheme_data = shared_dict[_]['fiscal_year'][year]
                    shared_dict[_]['fiscal_year'][year] = {}

                    for scheme in schemes_sequence:
                        if scheme not in scheme_data.keys():
                            continue

                        # Because CKAN names don't have `_` for these schemes
                        scheme_name = scheme
                        if scheme == 'sbm_g' or scheme == 'sbm_u':
                            scheme_name = scheme.replace('_', '')

                        shared_dict[_]['fiscal_year'][year].update({scheme_name: scheme_data[scheme]})

            final_dict = {
                'state_avg': state_average_dict,
                'district_name_data': shared_dict
            }
            
            with open(
                merged_json_files_directory + '/' + file[:-4].replace('-', '_') + '.json', 'w+'
            ) as fp:
                json.dump(final_dict, fp)

if __name__ == "__main__":
    main()