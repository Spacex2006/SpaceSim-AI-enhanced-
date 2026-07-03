# SpaceSim build

CXX      := g++
CXXSTD   := c++23
CXXFLAGS := -std=$(CXXSTD) -Wall -Wextra -O2 -Isrc -pthread
LDFLAGS  := -pthread
LDLIBS   := -lm

TARGET  := .bin/spacesim
SRCDIR  := src
OBJDIR  := .build

# Find all .cpp sources under src/ and map them to build/*.o
SRCS := $(shell find $(SRCDIR) -name '*.cpp')
OBJS := $(patsubst $(SRCDIR)/%.cpp,$(OBJDIR)/%.o,$(SRCS))
DEPS := $(OBJS:.o=.d)

.PHONY: all clean

all: $(TARGET)

# Link
$(TARGET): $(OBJS)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $^ -o $@ $(LDLIBS)

# Compile (-MMD -MP generates header dependency files)
$(OBJDIR)/%.o: $(SRCDIR)/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@

clean:
	rm -rf $(OBJDIR) $(TARGET)

-include $(DEPS)
