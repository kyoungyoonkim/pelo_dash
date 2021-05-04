import csv
import pandas as pd
import time
import os

class GreedyHeuristic():

    def __init__(self):
        self.solution_list = []
        self.show_status = 0

    def get_sender_routes(self, strategy, df_routes, sender, dict_sender_type, dict_receiver_type, df_capacity):
        df = df_routes[(df_routes['sender'] == sender)]
        series_capacity = df_capacity.groupby(df_capacity['receiver'])['receiverCapacity'].sum()

        if strategy == 0:
            df1 = df
            pass
        elif strategy == 1:
            sender_type = dict_sender_type[sender]
            list_receiver_same_type = [key for key, value in dict_receiver_type.items() if value == sender_type]
            df1 = df[df['receiver'].isin(list_receiver_same_type)]
        elif strategy == 2:
            sender_type = dict_sender_type[sender]
            if sender_type == 'HOSPITAL':
                list_receiver_same_type = [key for key, value in dict_receiver_type.items() if value == 'HOSPITAL']
                df1 = df[df['receiver'].isin(list_receiver_same_type)]
            elif sender_type == 'NH':
                df1 = df

        df1['capacity'] = df1['receiver'].map(series_capacity)
        df1['weight1'] = df1['c_1'] / df1['capacity']
        df1['weight2'] = df1['c_1'] / (df1['capacity'] ** 2)

        df1.reset_index(drop=True)
        return df1

    def check_ambus_transportation(self, dict_vehicleCap, num_ambus, num_demand):
        dict_solutions = {}
        for key, val in dict_vehicleCap.items():
            if key != 'v00':
                sol = int(num_demand / val)
                remainder = num_demand - (val * sol)
                dict_solutions[key] = [sol, remainder]

        list_sols = [dict_solutions[key][0] for key in dict_solutions.keys()]
        list_remainders = [dict_solutions[key][1] for key in dict_solutions.keys()]

        # demand cannot be transported by ambus
        if max(list_sols) == 0:
            dict_solution_output = {'vehicleType': 'v00',
                                    'value': max(list_remainders),
                                    'RemainingAmbus': num_ambus,
                                    'remainder': 0}

            return dict_solution_output

        # number of remaining ambus = 0
        if num_ambus == 0:
            dict_solution_output = {'vehicleType': 'v00',
                                    'value': num_demand,
                                    'RemainingAmbus': num_ambus,
                                    'remainder': 0}

        # number of remaining ambus != 0
        else:
            max_divider = 0
            max_solution = 0

            for key, val in dict_solutions.items():
                if (val[0] != 0) & (dict_vehicleCap[key] >= max_divider):
                    max_divider_key = key
                    max_divider = dict_vehicleCap[key]
                    max_solution = val[0]

            if num_ambus >= max_solution:
                remaining_ambus = num_ambus - max_solution
            else:
                max_solution = num_ambus
                remaining_ambus = 0

            remainder = num_demand - max_divider * max_solution
            dict_solution_output = {'vehicleType': max_divider_key,
                                    'value': max_solution,
                                    'RemainingAmbus': remaining_ambus,
                                    'remainder': remainder}

        return dict_solution_output

    def assign_receiver_n(self,
                          df_route_by_sender,
                          num_demand,
                          input_scenario,
                          df_capacity,
                          dict_vehicleCap,
                          num_ambus,
                          input_sort_column):

        patient_type = 'n'
        sort_column = input_sort_column

        if self.show_status == 1:
            print('INPUT DEMAND TO ASSIGN: %s,  %s' % (num_demand, patient_type))

        while num_demand != 0:
            vehicle_sol = self.check_ambus_transportation(dict_vehicleCap, num_ambus, num_demand)
            input_df_route_sender = df_route_by_sender[df_route_by_sender['vehicleType'] == vehicle_sol['vehicleType']]
            input_df_route_sender = input_df_route_sender.sort_values(by=sort_column)
            input_df_route_sender.reset_index(drop=True)

            num_vehicle_used = vehicle_sol['value']
            demand_to_remove = dict_vehicleCap[vehicle_sol['vehicleType']] * num_vehicle_used

            for index, row in input_df_route_sender.iterrows():
                this_staging, this_vehicle_type, this_sender, this_receiver = row['stagingArea1'], row['vehicleType'], row['sender'], row['receiver']
                try:
                    this_capacity = df_capacity.loc[(df_capacity['receiver'] == this_receiver) & (df_capacity['patientType'] == patient_type)]['receiverCapacity'].values[0]
                except IndexError:
                    continue

                if vehicle_sol['vehicleType'] == 'v00':

                    demand_assigned = min(this_capacity, demand_to_remove)

                    # update capacity
                    df_capacity.loc[(df_capacity['receiver'] == this_receiver) & (df_capacity['patientType'] == patient_type), 'receiverCapacity'] = this_capacity - demand_assigned
                    sol_string = [this_staging, this_sender, this_receiver, this_staging, this_vehicle_type, patient_type, input_scenario, demand_assigned]
                    self.solution_list.append(sol_string)
                    num_demand = num_demand - demand_assigned
                    demand_to_remove = num_demand

                    if self.show_status == 1:
                        print('AMBULANCE | SINGLE TRIP | demand assigned %s | demand remaining %s' % (demand_assigned, num_demand))

                    if num_demand == 0:
                        break

                else:
                    if this_capacity >= demand_to_remove:

                        # define demand assigned and vehicles used
                        demand_assigned = demand_to_remove
                        ambus_used = int(demand_to_remove / dict_vehicleCap[vehicle_sol['vehicleType']])

                        # write solution
                        sol_string = [this_staging, this_sender, this_receiver, this_staging, this_vehicle_type, patient_type, input_scenario, ambus_used]
                        self.solution_list.append(sol_string)

                        # update capacity
                        remaining_capacity = this_capacity - demand_assigned
                        df_capacity.loc[(df_capacity['receiver'] == this_receiver) & (df_capacity['patientType'] == patient_type), 'receiverCapacity'] = remaining_capacity

                        # update demand
                        num_demand = num_demand - demand_assigned

                        # update vehicles
                        num_ambus = num_ambus - ambus_used

                        if self.show_status == 1:
                            print('AMBUS | SINGLE TRIP (ENOUGH CAP) | demand assigned %s | demand remaining %s' % (demand_assigned, num_demand))

                        break

                    else:

                        for i in range(vehicle_sol['value']):
                            this_lot = dict_vehicleCap[vehicle_sol['vehicleType']] * (i + 1)

                            if this_capacity < this_lot:
                                this_ambus_used = i
                                demand_by_ambus = dict_vehicleCap[vehicle_sol['vehicleType']] * i
                                break

                        # define demand assigned and vehicles used
                        demand_assigned = demand_by_ambus
                        ambus_used = this_ambus_used

                        # write solution
                        sol_string = [this_staging, this_sender, this_receiver, this_staging, this_vehicle_type, patient_type, input_scenario, ambus_used]
                        self.solution_list.append(sol_string)

                        # update capacity
                        remaining_capacity = this_capacity - demand_assigned
                        df_capacity.loc[(df_capacity['receiver'] == this_receiver) & (df_capacity['patientType'] == patient_type), 'receiverCapacity'] = remaining_capacity

                        # update demand
                        num_demand = num_demand - demand_assigned
                        demand_to_remove = demand_to_remove - demand_assigned

                        # update vehicles
                        num_ambus = num_ambus - ambus_used

                        if self.show_status == 1:
                            print('AMBUS | SINGLE TRIP (SMALL CAP) | demand assigned %s | demand remaining %s' % (demand_assigned, num_demand))

        return [df_capacity, num_ambus]

    def assign_receiver_c(self,
                          df_route_by_sender,
                          num_demand,
                          input_scenario,
                          df_capacity,
                          dict_vehicleCap,
                          num_ambus,
                          input_sort_column):

        patient_type = 'c'
        sort_column = input_sort_column

        input_df_route_sender = df_route_by_sender[df_route_by_sender['vehicleType'] == 'v00']
        input_df_route_sender = input_df_route_sender.sort_values(by=sort_column)
        input_df_route_sender.reset_index(drop=True)

        if self.show_status == 1:
            print('INPUT DEMAND TO ASSIGN: %s,  %s' % (num_demand, patient_type))

        for index, row in input_df_route_sender.iterrows():

            # determine capacity vs demand
            this_staging, this_vehicle_type, this_sender, this_receiver = row['stagingArea1'], row['vehicleType'], row['sender'], row['receiver']

            # update capacity
            try:
                this_capacity = df_capacity.loc[(df_capacity['receiver'] == this_receiver) & (df_capacity['patientType'] == patient_type)]['receiverCapacity'].values[0]
            except IndexError:
                continue
            demand_to_assign = min(this_capacity, num_demand)
            df_capacity.loc[(df_capacity['receiver'] == this_receiver) & (df_capacity['patientType'] == patient_type), 'receiverCapacity'] = this_capacity - demand_to_assign

            # update demand
            num_demand = num_demand - demand_to_assign

            # update solution list
            sol_string = [this_staging, this_sender, this_receiver, this_staging, this_vehicle_type, patient_type, input_scenario, demand_to_assign]
            self.solution_list.append(sol_string)

            if self.show_status == 1:
                print('AMBULANCE | SINGLE TRIP | demand assigned %s | demand remaining %s' % (demand_to_assign, num_demand))

            if num_demand == 0:
                break

        return [df_capacity, num_ambus]

    def get_vehicles_used(self, input_df_solution, input_list_scenarios, dict_vehicleCap):
        # Calculate vehicles used per scenario
        list_vehicles = list(dict_vehicleCap.keys())
        list_solutions = [input_df_solution]

        dict_vehicles_used = {}

        for s in input_list_scenarios:

            dict_vehicles_scenario = {}
            for vehicle in list_vehicles:
                num_v = 0

                for df in list_solutions:
                    df1 = df[(df['scenario'] == s) & (df['vehicleType'] == vehicle)]
                    num_v = num_v + sum(df1['value'])

                dict_vehicles_scenario[vehicle] = num_v

            dict_vehicles_used[s] = dict_vehicles_scenario

        # Calculate max vehicles used
        max_vehicles = {}

        for vehicle in list_vehicles:
            max_vehicle = 0

            for s, inner_dict in dict_vehicles_used.items():
                current_max = inner_dict[vehicle]

                if current_max > max_vehicle:
                    max_vehicle = current_max

                else:
                    continue

            max_vehicles[vehicle] = max_vehicle

        return max_vehicles

    def get_objective_value(self, input_df_solution, input_staging_area, input_max_vehicles):
        # fixed_cost
        file = 'input_openingCost.tab'
        df_fixed_cost = pd.read_csv(self.path + file, delimiter='\t')
        dict_fixed_cost = dict(zip(df_fixed_cost['stagingArea'], df_fixed_cost['openingCost']))

        # resource_cost
        file = 'input_c_v.tab'
        df_resource_cost = pd.read_csv(self.path + file, delimiter='\t')
        dict_resource_cost = dict(zip(df_resource_cost['vehicleType'], df_resource_cost['c_v']))
        resource_cost = 0
        for key, value in dict_resource_cost.items():
            temp_resource_cost = value * input_max_vehicles[key]
            resource_cost = resource_cost + temp_resource_cost

        # operation_cost
        file = 'input_c1.tab'
        df_routes = pd.read_csv(self.path + file, delimiter='\t')
        df_routes = df_routes[df_routes['stagingArea1'].isin(input_staging_area)]
        list_keys = ['stagingArea1', 'sender', 'receiver', 'vehicleType']
        df_routes['key'] = list(zip(df_routes[list_keys[0]], df_routes[list_keys[1]], df_routes[list_keys[2]], df_routes[list_keys[3]]))
        dict_route_cost = dict(zip(df_routes['key'], df_routes['c_1']))

        file = 'input_probability.tab'
        df_probability = pd.read_csv(self.path + file, delimiter='\t')
        dict_probability = dict(zip(df_probability['scenario'], df_probability['probability']))

        list_scenarios = list(input_df_solution['scenario'].unique())
        operating_cost = 0
        for s in list_scenarios:
            dff = input_df_solution.loc[input_df_solution['scenario'] == s]

            scenario_sum = 0
            dff['key'] = list(zip(dff['staging'], dff['sender'], dff['receiver'], dff['vehicleType']))
            dict_dff_solution = dict(zip(dff['key'], dff['value']))

            for key, value in dict_dff_solution.items():
                scenario_sum = scenario_sum + value * dict_route_cost[key]

            operating_cost = operating_cost + dict_probability[s] * scenario_sum

        # Find total objective value
        fixed_cost = sum(list(dict_fixed_cost[i] for i in input_staging_area))

        objective_value = fixed_cost + resource_cost + operating_cost
        # print(fixed_cost, '\t', resource_cost, '\t', operating_cost, '\t', objective_value)

        return objective_value

    def sanity_check(self, input_df_solution):

        # input_df_solution columns : ['staging', 'sender', 'receiver', 'staging1', 'vehicleType', 'patientType', 'scenario', 'value']
        file = 'input_ambulanceCapacity.tab'
        df_vehicleCapacity = pd.read_csv(self.path + file, delimiter='\t')
        dict_vehicleCap = dict(zip(df_vehicleCapacity['ambulanceType'], df_vehicleCapacity['capacity']))

        # DEMANDS
        file = 'input_demand_vs.tab'
        df_demand = pd.read_csv(self.path + file, delimiter='\t')
        df_demand = df_demand[df_demand['demand'] != 0]
        list_scenarios = list(df_demand['scenario'].unique())
        list_scenarios.sort()
        list_patient_type = ['n', 'c']

        error_indicator = 0
        for s in list_scenarios:
            for p in list_patient_type:
                sum_demand = sum(df_demand.loc[(df_demand['scenario'] == s) & (df_demand['patientType'] == p)]['demand'])
                dff = input_df_solution.loc[(input_df_solution['scenario'] == s) & (input_df_solution['patientType'] == p)]
                sum_solution = sum(dff['vehicleType'].map(dict_vehicleCap) * dff['value'])
                # sum_solution = sum(input_df_solution.loc[(input_df_solution['scenario'] == s) & (input_df_solution['patientType'] == p)]['value'])

                if sum_demand != sum_solution:
                    print("Error in ", s, p, "sum_demand, sum_solution: ", sum_demand, sum_solution)
                    error_indicator = 1
        if error_indicator == 0:
            print("NO ERROR IN SOLUTION")

    def get_max_flooded_location(self):

        file = 'scenario_lookup.tab'
        df = pd.read_csv(self.path + file, delimiter='\t')
        list_s = list(df['scenario'].unique())

        dict_flooded = {}
        max_num = 0
        for s in list_s:
            df0 = df[df['scenario'] == s]
            dict_flooded[s] = list(df0['sender'])
            if len(df0) > max_num:
                max_num = len(df0)
                output_max_scenario = s

        return [dict_flooded, output_max_scenario]

    def get_staging_areas(self, input_dict_flooded, input_max_scenario, input_staging_area, input_num_staging_areas):
        # GET MINIMUM SUM OF DISTANCES FROM THE SCENARIO
        file = 'input_c_ijv.tab'
        df_distance = pd.read_csv(self.path + file, delimiter='\t')

        list_staging = list(df_distance['stagingArea'].unique())
        num_staging_areas = input_num_staging_areas

        dict_stagingArea_distance = {}
        vehicle = 'v00'
        for i in list_staging:
            df0 = df_distance[df_distance['stagingArea'] == i]
            summation = 0

            for j in input_dict_flooded[input_max_scenario]:
                summation = summation + df0[(df0['sender'] == j) & (df0['vehicleType'] == vehicle)]['c_ijv'].values[0]

            dict_stagingArea_distance[i] = summation

        sorted_stagingArea_distance = {k: v for k, v in sorted(dict_stagingArea_distance.items(), key=lambda item: item[1])}
        print(sorted_stagingArea_distance)
        staging_area = list(sorted_stagingArea_distance.keys())[0:num_staging_areas]

        # override staging_area location if there's input staging area
        if len(input_staging_area) != 0:
            output_staging_area = input_staging_area
        else:
            output_staging_area = staging_area

        print("")
        print("STAGING AREA: ", output_staging_area)
        print("")

        return output_staging_area

    def get_solution(self, input_parent_directory, input_directory, input_staging_area, input_strategy, column_to_sort, number_staging_areas):
        # ----------------------------------------------
        # STEP 0: Initialize input
        # ----------------------------------------------
        strategy = input_strategy
        path = '%s%s/input/' % (input_parent_directory, input_directory)
        self.path = path

        # ----------------------------------------------
        # STEP 1: Get scenario with max number of flooded locations
        # ----------------------------------------------
        output = self.get_max_flooded_location()
        dict_flooded = output[0]
        max_scenario = output[1]

        # ----------------------------------------------
        # STEP 2: Get staging area from the max_scenario
        # ----------------------------------------------
        list_staging_area = self.get_staging_areas(dict_flooded, max_scenario, input_staging_area, number_staging_areas)

        # ----------------------------------------------
        # STEP 3: Initialize input data
        # ----------------------------------------------
        time_enumeration_start = time.time()

        # AMBUS CAPACITY
        file = 'input_ambulanceCapacity.tab'
        df_vehicleCapacity = pd.read_csv(path + file, delimiter='\t')
        dict_vehicleCap = dict(zip(df_vehicleCapacity['ambulanceType'], df_vehicleCapacity['capacity']))

        # ROUTES(PATHS) WITH STAGING AREA FOUND
        file = 'input_c1.tab'
        df_routes = pd.read_csv(path + file, delimiter='\t')
        df_routes = df_routes[df_routes['stagingArea1'].isin(list_staging_area)]

        # DEMANDS
        file = 'input_demand_vs.tab'
        df_demand = pd.read_csv(path + file, delimiter='\t')
        df_demand = df_demand[df_demand['demand'] != 0]
        list_scenarios = list(df_demand['scenario'].unique())
        list_scenarios.sort()

        # SENDER/RECEIVER TYPES
        file = 'df_sender.csv'
        df_sender = pd.read_csv(path + file)
        dict_sender_type = dict(zip(df_sender['code'], df_sender['type']))

        file = 'df_receiver.csv'
        df_receiver = pd.read_csv(path + file)
        dict_receiver_type = dict(zip(df_receiver['code'], df_receiver['type']))

        # ----------------------------------------------
        # STEP 4: START THE ALGORITHM
        # ----------------------------------------------
        print("START ALGORITHM")
        print("")
        count_scenario = 0

        for s in list_scenarios:
            time_scenario_start = time.time()
            print('SCENARIO: ', s)
            count_scenario = count_scenario + 1

            # # Save status to external file
            # a_file = open('/Users/kyoung/Box Sync/github/dash/pelo/data/' + "run_status.csv", "w")
            # writer = csv.writer(a_file)
            # writer.writerow(['status', count_scenario])
            # a_file.close()

            # INITIALIZE PARAMETERS
            # PARAMETER 1 : RECEIVER CAPACITY
            file = 'input_receiverCapacity.tab'
            df_capacity = pd.read_csv(path + file, delimiter='\t')

            # PARAMETER 2: AMBUS CAPACITY
            file = 'input_ambusMax.tab'
            with open(path + file, newline='') as input_file:
                game_reader = csv.reader(input_file, delimiter='\t')
                for line in game_reader:
                    num_ambus = int(line[0])

            df_demand_s = df_demand[df_demand['scenario'] == s]
            list_senders = list(df_demand_s['sender'].unique())

            # ORDER SENDERS BY DEMAND
            dict_senders = {}
            for q in list_senders:
                dict_senders[q] = sum(df_demand_s[df_demand_s['sender'] == q]['demand'].values)

            dict_senders_ordered = {k: v for k, v in sorted(dict_senders.items(), key=lambda item: item[1], reverse=True)}
            list_senders_ordered = list(dict_senders_ordered.keys())

            for j in list_senders_ordered:

                if self.show_status == 1:
                    print(j)

                df_route_by_sender = self.get_sender_routes(strategy, df_routes, j, dict_sender_type, dict_receiver_type, df_capacity)
                df_demand_sj = df_demand_s[df_demand_s['sender'] == j]
                list_patient_type_sender = list(df_demand_sj['patientType'])

                for p in list_patient_type_sender:
                    if p == 'c':
                        check_num_demand = df_demand_sj[df_demand_sj['patientType'] == p]['demand'].values[0]
                        output = self.assign_receiver_c(df_route_by_sender, check_num_demand, s, df_capacity, dict_vehicleCap, num_ambus, column_to_sort)
                        df_capacity = output[0]
                        df_capacity = df_capacity.loc[df_capacity['receiverCapacity'] != 0]
                        num_ambus = output[1]

                    else:
                        check_num_demand = df_demand_sj[df_demand_sj['patientType'] == p]['demand'].values[0]
                        output = self.assign_receiver_n(df_route_by_sender, check_num_demand, s, df_capacity, dict_vehicleCap, num_ambus, column_to_sort)
                        df_capacity = output[0]
                        df_capacity = df_capacity.loc[df_capacity['receiverCapacity'] != 0]
                        num_ambus = output[1]

            time_scenario_end = time.time()
            print("   SCENARIO TIME: ", time_scenario_end - time_scenario_start)

        time_enumeration_end = time.time()
        print("ENUMERATION TIME: ", time_enumeration_end - time_enumeration_start)

        # ----------------------------------------------
        # STEP 5: SAVE AND OUTPUT SOLUTION
        # ----------------------------------------------
        cols = ['staging', 'sender', 'receiver', 'staging1', 'vehicleType', 'patientType', 'scenario', 'value']
        df_solution = pd.DataFrame(self.solution_list, columns=cols)
        df_solution = df_solution.loc[df_solution['value'] != 0]

        # Output location
        output_path = '%s%s/output/' % (input_parent_directory, input_directory)
        output_file_name = 'df_result.csv'

        # Create a output directory
        try:
            os.mkdir(output_path)
        except OSError as error:
            print(error)

        # Save output
        df_solution.to_csv(output_path + output_file_name)
        print("Result is saved at %s%s" % (output_path, output_file_name))

        dict_max_vehicles = self.get_vehicles_used(df_solution, list_scenarios, dict_vehicleCap)
        obj_value = self.get_objective_value(df_solution, list_staging_area, dict_max_vehicles)
        print('OBJECTIVE VALUE %s' % obj_value)

        # return df_solution
        print('Run completed')
        return dict_max_vehicles, df_solution, obj_value


if __name__ == '__main__':

    time_heuristic_start = time.time()
    a = GreedyHeuristic()
    path = '/Users/kyoung/Box Sync/github/pelo_run/pelo_tests/'
    directory = 'test_default_ambusMax16_Iter[0]_Trip[single]_Opt[1]_AmbusCR[0]_Sender[all]_AmbusMin[20]_shelter[0]_g[1]'
    # path = '/Users/kyoung/Box Sync/github/dash/pelo/data/'
    # directory = 'case1'

    # path = '/Users/kyoung/Box Sync/github/pelo_run/'
    # directory = 'test_100_senders_v2_Iter[1]_Trip[double]_Opt[1]_AmbusCR[0]_Sender[all]_AmbusMin[20]_shelter[0]_g[1]'

    list_stg_areas = []
    routing_strategy = 1
    sort_column_type = 'weight1'
    input_staging_areas = 1

    print(directory)
    print("INPUT STAGING AREAS %s, STRATEGY %s, SORT BY %s" % (list_stg_areas, routing_strategy, sort_column_type))
    b = a.get_solution(path, directory, list_stg_areas, routing_strategy, sort_column_type, input_staging_areas)
    time_heuristic_end = time.time()
    a.sanity_check(b[1])
    print("ALGORITHM TIME: ", time_heuristic_end - time_heuristic_start)
