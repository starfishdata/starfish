from starfish.data_template.data_template_gen import data_template_generate
from starfish.data_template.topic_generator import TopicGeneratorInput
# results = get_city_info_wf.run(
#         # data=[{"city_name": "Berlin"}, {"city_name": "Rome"}],
#         # [{"city_name": "Berlin"}, {"city_name": "Rome"}],
#         city_name=["San Francisco", "New York", "Los Angeles"] * 50,
#         region_code=["DE", "IT", "US"] * 50,
#         # city_name="Beijing",  ### Overwrite the data key
#         # num_records_per_city = 3
#     )

result = data_template_generate.list()
print(result)
# get_city_info_wf = data_template_generate.get("starfish/get_city_info_wf")
# results = get_city_info_wf.run(
#         # data=[{"city_name": "Berlin"}, {"city_name": "Rome"}],
#         # [{"city_name": "Berlin"}, {"city_name": "Rome"}],
#         city_name=["San Francisco", "New York", "Los Angeles"] * 50,
#         region_code=["DE", "IT", "US"] * 50,
#         # city_name="Beijing",  ### Overwrite the data key
#         # num_records_per_city = 3
#     )

# input_data = TopicGeneratorInput(
#     community_name="AI Enthusiasts",
#     seed_topics=["Machine Learning", "Deep Learning"],
#     num_topics=5
# )
# topic_generator = data_template_generate.get("community/topic_generator")
# result = topic_generator.run(input_data)
# print(result)

topic_generator = data_template_generate.get("starfish/math_problem_gen_wf")
result = topic_generator.run()
print(result)
