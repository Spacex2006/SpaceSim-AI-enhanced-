#include "Bodies.h"
#include <fstream>
#include <iostream>
#include <string>
#include "nlohmann/json.hpp"

namespace SpaceSim{

    std::vector<Coordinate> center_of_mass(std::vector<CelestialBody>& bodies){
        Mass total_mass = std::ranges::fold_left(bodies, 0, [](auto x, auto body){ return x+body.mass; });
        Coordinate com_x = std::ranges::fold_left(bodies, 0, [](auto x, auto body){ return x+body.mass*body.position.x; })/total_mass;
        Coordinate com_y = std::ranges::fold_left(bodies, 0, [](auto x, auto body){ return x+body.mass*body.position.y; })/total_mass;
        Coordinate com_z = std::ranges::fold_left(bodies, 0, [](auto x, auto body){ return x+body.mass*body.position.z; })/total_mass;
        return {com_x, com_y, com_z};
    }
    std::vector<CelestialBody> load_bodies(const std::string& filepath){
        std::vector<CelestialBody> bodies;
        std::ifstream file(filepath);   //opening json file
        if(!file.is_open()){
            std::cerr<<"Error: Could not find the file at "<<filepath<<std::endl;
            return bodies;  //returns an empty list of bodies
        }
        nlohmann::json data;
        file>>data;
        int id=0;
        for(const auto& item:data){
            //iterating through the data to fill up the list
            double mass=item["mass"].get<double>();
            double radius=item["radius"].get<double>();
            Vector<Coordinate> position(item["px"].get<double>(),item["py"].get<double>(),item["pz"].get<double>());
            Vector<Coordinate> velocity(item["vx"].get<double>(),item["vy"].get<double>(),item["vz"].get<double>());
            double rotation_speed=item["rotation_speed"].get<double>();
            double orbital_tilt=item["orbital_tilt"].get<double>();
            //saving the data in the list
            bodies.emplace_back(id,mass,radius,position,velocity,rotation_speed,orbital_tilt);
            id++;
        }
        //returns list of bodies
        return bodies;
    }
}