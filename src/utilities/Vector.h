#include<iostream>
#include<type_traits>
#include<cmath>
#pragma once

namespace  SpaceSim{
    template<typename T> 
    concept Number = std::is_arithmetic_v<T>;

    template<Number T>
    class Vector{
        public:
            T x, y, z;
            Vector():x{0}, y{0}, z{0}{}
            Vector(T _x, T _y, T _z): x(_x), y{_y}, z{_z}{}
            Vector<T>& operator+=(const Vector<T> &other){
                this->x+=other.x;
                this->y+=other.y;
                this->z+=other.z;
                return *this;
            }
            Vector<T>& operator-=(const Vector<T> &other){
                this->x-=other.x;
                this->y-=other.y;
                this->z-=other.z;
                return *this;
            }
            T dot(const Vector<T> &other) const{
                return x*other.x+ y*other.y+ z*other.z;
            }
             T norm() const{
                return std::sqrt(this->x*this->x+this->y*this->y+this->z*this->z);
            }
            T square() const{
                return (x*x+y*y+z*z);
            }
            Vector<T>& operator=(const Vector<T>& other)=default;

            Vector<T> operator+(Vector<T> other) const{
                return other+=*this;
            }
            Vector<T> operator-(Vector<T> other) const{
                Vector<T> copy = *this;
                return copy-=other;
            }
            Vector<T> operator/(T data) const{
                return {this->x/data, this->y/data, this->z/data};
            }
            template<Number U>
            friend Vector<T>operator*(U data, const Vector<T>& other){
                return {other.x*data, other.y*data, other.z*data};
            }
            template<Number U>
            friend Vector<T> operator*(const Vector<T>& other, U data){
                 return {other.x*data, other.y*data, other.z*data};
            }
    };
   

}