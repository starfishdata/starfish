from starfish.data_template.template_gen import data_gen_template
# from starfish.data_template.topic_generator import TopicGeneratorInput
# results = get_city_info_wf.run(
#         # data=[{"city_name": "Berlin"}, {"city_name": "Rome"}],
#         # [{"city_name": "Berlin"}, {"city_name": "Rome"}],
#         city_name=["San Francisco", "New York", "Los Angeles"] * 50,
#         region_code=["DE", "IT", "US"] * 50,
#         # city_name="Beijing",  ### Overwrite the data key
#         # num_records_per_city = 3
#     )

result = data_gen_template.list()
print(result)
# get_city_info_wf = data_gen_template.get("starfish/get_city_info_wf")
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
# topic_generator = data_gen_template.get("community/topic_generator")
# result = topic_generator.run(input_data)
# print(result)

# get a template cls and call the func.run using pre/post hook
topic_generator = data_gen_template.get("starfish/math_problem_gen_wf")
result = topic_generator.run()
print(result)
