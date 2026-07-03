#include "Space/Bodies.h"
#include "Space/Forces.h"
#include "utilities/constants.h"
#include "utilities/Vector.h"
#include <fstream>
#include<iostream>
using namespace SpaceSim;
int main(){
    //opening file to store data to visualise
    std::ofstream outfile("data/simulation_output.csv");
    outfile << "step,body_id,x,y,z\n";

    //loading boadies
    std::cout<<"Loading bodies"<<std::endl;
    auto bodies=load_bodies("data/solar_system.json");
    std::cout<<"Loaded "<<bodies.size()<<" bodies.\n";

    //setting up
    double dt=SECONDS_PER_DAY; //time between two calculations
    int total_steps=365*1000;//n.o. of steps ofc

    //initial calculations before the loop
    std::vector<SpaceSim::Vector<double>> forces=SpaceSim::calculate_forces(bodies);
    std::vector<SpaceSim::Vector<double>> accelerations(bodies.size());
    for(size_t i=0;i<bodies.size();i++){
        accelerations[i]=forces[i]*(1.0/bodies[i].mass);
    }

    //loop which uses leapfrog which allows for energy conservation
    //allowing for longer simulation times
    for(int step=0;step<total_steps;step++){
        for(size_t i=0;i<bodies.size();i++){
            bodies[i].velocity+=accelerations[i]*(dt/2.0);
        }
        for(size_t i=0;i<bodies.size();i++){
            bodies[i].position+=bodies[i].velocity*dt;
        }
        forces=SpaceSim::calculate_forces(bodies);
        for(size_t i=0;i<bodies.size();i++){
            accelerations[i]=forces[i]*(1.0/bodies[i].mass);
        }
        for(size_t i=0;i<bodies.size();i++){
            bodies[i].velocity+=accelerations[i]*(dt/2.0);
        }
        //storing data in csv file for later analysis
        for(size_t i=0;i<bodies.size();i++){
            outfile << step << ","
                    << bodies[i].id << ","
                    << bodies[i].position.x << ","
                    << bodies[i].position.y << ","
                    << bodies[i].position.z << "\n";
        }
    }
    outfile.close();
    std::cout << "Simulation complete. Data written to data/simulation_output.csv\n";
    return 0;
}