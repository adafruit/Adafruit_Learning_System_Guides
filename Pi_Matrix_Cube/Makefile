RGB_LIB_DISTRIBUTION=../rpi-rgb-led-matrix
RGB_INCDIR=$(RGB_LIB_DISTRIBUTION)/include
RGB_LIBDIR=$(RGB_LIB_DISTRIBUTION)/lib
RGB_LIBRARY_NAME=rgbmatrix
CXXFLAGS=-Wall -Ofast -fomit-frame-pointer -I$(RGB_INCDIR)
LDFLAGS+=-L$(RGB_LIBDIR) -l$(RGB_LIBRARY_NAME) -lrt -lm -lpthread

EXECS = globe life

all: $(EXECS)

globe: globe.cc
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDFLAGS) -ljpeg
	strip $@

life: life.cc
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDFLAGS)
	strip $@

clean:
	rm -f $(EXECS)
