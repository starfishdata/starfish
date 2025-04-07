### Prototype user flow for each user case
from starfish.core.structured_llm import StructuredLLM

### Use Case 1: Parallel Kwargs 
@generator()
def workflow(city_name):
    structured_llm = StructuredLLM(
        model = 'gpt-4o',
        prompt = 'Given the city name {{city_name}}, please generate the country code',
        output_schema = [{'name': 'country_code', 'type': 'string'}]
    )
    output_data = structured_llm.run(city_name = city_name)

    return output_data.data 
### It will have 3 records in total
data = workflow.run(city_name = ['San Francisco', 'New York', 'Los Angeles'])


### Use Case 2: Parallel + Broadcast Kwargs
@generator()
def workflow(city_name, num_records_per_city):
    structured_llm = StructuredLLM(
        model = 'gpt-4o',
        prompt = 'Given the city name {{city_name}}, please generate fun facts about the city',
        output_schema = [{'name': 'fun_facts', 'type': 'string'}]
    )
    output_data = structured_llm.run(city_name = city_name, num_records = num_records_per_city)
    return output_data.data 
### Each city will have 3 fun facts so 9 records in total
data = workflow.run(city_name = ['San Francisco', 'New York', 'Los Angeles'], num_records_per_city = 3)


### Use Case 3: data=List[Dict] Only 
data = workflow.run([
    {'city_name': 'Paris'},
    {'city_name': 'Tokyo'}
])

### Use Case 4: data=List[Dict] + Broadcast Kwarg
data = workflow.run([
    {'city_name': 'Paris'},
    {'city_name': 'Tokyo'}
], num_records_per_city = 3)


### Use Case 5: data (List[Dict]) + Parallel Kwarg (Matching Lengths)
@generator()
def get_city_info_wf(city_name, region_code):
    structured_llm = StructuredLLM(
        model = 'gpt-4o',
        prompt = 'Get state/province for {{city_name}} in region {{region_code}}.',
        output_schema = [{'name': 'state_province', 'type': 'string'}]
    )
    output = structured_llm.run(city_name=city_name, region_code=region_code)
    return output.data

get_city_info_wf.run(
    data = [
    {'city_name': 'Berlin'}, # Note: No region_code here
    {'city_name': 'Rome'}
],
    regions = ['DE', 'IT']
)

### Use Case 6: data + Parallel Kwarg + Broadcast Kwarg
@generator()
def get_city_info_wf(city_name, region_code, num_records_per_city):
    structured_llm = StructuredLLM(
        model = 'gpt-4o',
        prompt = 'Get state/province for {{city_name}} in region {{region_code}}.',
        output_schema = [{'name': 'state_province', 'type': 'string'}]
    )
    output = structured_llm.run(city_name=city_name, region_code=region_code, num_records=num_records_per_city)
    return output.data


get_city_info_wf.run(
    data = [
    {'city_name': 'Berlin'}, # Note: No region_code here
    {'city_name': 'Rome'}
],
    regions = ['DE', 'IT'],
    num_records_per_city = 3
)

### Use Case 7: Kwarg Override (Broadcast Kwarg vs data key)

get_city_info_wf.run(
    data = [
    {'city_name': 'Berlin'}, 
    {'city_name': 'Rome'}
],
    regions = ['DE', 'IT'],
    city_name = 'Beijing', ### Overwrite the data key
    num_records_per_city = 3
)

## Invoke sequence
# data =[
#     {'city_name': 'Berlin'}, 
#     {'city_name': 'Rome'}
# ]

# data =[
#     {'city_name': 'Berlin', 'region_code': 'DE'}, 
#     {'city_name': 'Rome', 'region_code': 'IT'}
# ]

# data =[
#     {'city_name': 'Beijing', 'region_code': 'DE'}, 
#     {'city_name': 'Beijing', 'region_code': 'IT'}
# ]

# data =[
#     {'city_name': 'Beijing', 'region_code': 'DE', 'num_records_per_city': 3}, 
#     {'city_name': 'Beijing', 'region_code': 'IT', 'num_records_per_city': 3}
# ]


### DataFactory input:
###     Data: List[Dict], Tuple[Dict]
###     Kwargs: List / Tuple or single value (int / string)

### if kwarg value is list -> parallel, if single -> broadcast, always
### Make sure the length of list/tuple is the same (across Data and Kwargs List input)
### Overwrite, if key conflict, Kwargs value will overwrite Data value, and if within Kwargs, broadcast will overwrite parallel

# 1. Parallel Sources: data=List[Dict] (if provided) AND any kwarg with a List/Tuple value.
# 2. Broadcast Sources: Any kwarg with a single value (not List/Tuple).
# 3. Length Constraint: All parallel sources MUST have the same length (L). Batch size is L (or 1 if no parallel sources).
# 4. Execution: Run L times.
# Args Assembly (iter i): Start with data[i] (if exists), merge/override with parallel kwargs[key][i], merge/override with broadcast kwargs[key].
# Override Order: Broadcast Kwarg > Parallel Kwarg > data Dict Value.
