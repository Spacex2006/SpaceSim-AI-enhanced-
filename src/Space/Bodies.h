#include<cstdint>
#include<vector>
#include<algorithm>
#include "utilities/Vector.h"
#include<ranges>
#pragma once
namespace SpaceSim{
    using Length = double;
    using Mass = double;
    using Energy = double;
    using Angle = double;
    using Coordinate = double;
    struct CelestialBody {
        int id;
        Length radius;
        Vector<Coordinate> position;
        Mass mass;
        Vector<Coordinate> velocity;
        Coordinate rotation_speed;
        Angle orbital_tilt;

        CelestialBody(int _id, Mass m, Length r, const Vector<Coordinate>& p, const Vector<Coordinate>& v, Coordinate rot = 0, Angle tilt = 0)
            : id(_id), radius(r), position(p), mass(m), velocity(v), rotation_speed(rot), orbital_tilt(tilt) {}
    };
    std::vector<Coordinate> center_of_mass(std::vector<CelestialBody>& bodies);
    std::vector<CelestialBody> load_bodies(const std::string& filepath);
}