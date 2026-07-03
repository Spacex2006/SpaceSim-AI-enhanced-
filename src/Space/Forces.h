#pragma once
#include "utilities/constants.h"
#include "Space/Bodies.h"
#include<vector>
#include<cmath>
#include<algorithm>
#include<execution>
#include<numeric>
namespace SpaceSim{ 

    Vector<double> gravity_calculator(const SpaceSim::CelestialBody& body_1,const SpaceSim::CelestialBody& body_2){
      return (G*body_1.mass*body_2.mass*(body_2.position-body_1.position))/pow((body_2.position-body_1.position).norm(),3);
    }
    //calculate force with id./ 
    void calculate_force_on_one(const std::vector<SpaceSim::CelestialBody>& bodies, int id, Vector<double>& return_value){
       auto x =  std::find_if(bodies.begin(), bodies.end(), [id](auto x){
            return x.id==id;
        });
      
       Vector<double> total_force{};
       std::for_each(bodies.begin(), bodies.end(), [&](const SpaceSim::CelestialBody& current_body){
            if(current_body.id!=id){
                total_force+=gravity_calculator(*x, current_body);
            }
       });
       return_value = total_force;
    }
    //force on indexed object
     void calculate_force_on_one_index(const std::vector<SpaceSim::CelestialBody>& bodies, int id, Vector<double>& return_value){
    
      
       Vector<double> total_force{};
       std::for_each(bodies.begin(), bodies.end(), [&](const SpaceSim::CelestialBody& current_body){
            if(current_body.id!= bodies[id].id){
                total_force+=gravity_calculator(bodies[id], current_body);
            }
       });
       return_value = total_force;
    }


    std::vector<Vector<double>> calculate_forces(const std::vector<SpaceSim::CelestialBody>& bodies){
        std::vector<size_t> indices(bodies.size(), 0);
        std::iota(indices.begin(), indices.end(), 0);
        std::vector<Vector<double>> forces(bodies.size(), {0.0, 0.0,0.0});
        std::for_each(std::execution::par, indices.begin(), indices.end(), [&](auto index){
            calculate_force_on_one_index(bodies, index,  forces[index]);
        });
        return forces;
    }
}