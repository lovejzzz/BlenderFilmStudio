// Trusted diagnostic reader, not a scene executor or simulation component.
#include <openvdb/openvdb.h>
#include <openvdb/io/File.h>
#include <openvdb/points/PointConversion.h>
#include <openvdb/points/PointAttribute.h>
#include <CommonCrypto/CommonDigest.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace v = openvdb;
using Points = v::points::PointDataGrid;
using Row = std::array<double, 7>;
void require(bool condition, const char* text) { if (!condition) throw std::runtime_error(text); }
struct Hash {
  CC_SHA256_CTX ctx;
  Hash() { CC_SHA256_Init(&ctx); }
  void number(double n) {
    require(std::isfinite(n), "nonfinite field");
    if (n == 0) n = 0; // Canonical positive zero.
    uint64_t bits; std::memcpy(&bits, &n, 8);
    unsigned char b[8]; for (int i=0;i<8;++i) b[i]=(bits>>(i*8))&255;
    CC_SHA256_Update(&ctx,b,8);
  }
  std::string finish() {
    unsigned char b[32]; CC_SHA256_Final(b,&ctx);
    std::ostringstream out; out<<std::hex<<std::setfill('0');
    for (auto n:b) out<<std::setw(2)<<int(n);
    return out.str();
  }
};
std::string safe(const std::string& s) {
  require(!s.empty() && s.size()<128, "invalid name");
  for (unsigned char c:s) require(std::isalnum(c)||c=='_'||c==':'||c=='.', "invalid name character");
  return '"'+s+'"';
}
void metadata(v::GridBase& grid, const v::Vec3i& dims, float voxel) {
  grid.setTransform(v::math::Transform::createLinearTransform(voxel));
  grid.insertMeta("file_base_resolution",v::Vec3IMetadata(dims));
  grid.insertMeta("file_voxel_size",v::FloatMetadata(voxel));
}
std::string inspect(v::GridBase::Ptr grid) {
  auto dims=grid->metaValue<v::Vec3i>("file_base_resolution");
  auto voxel=grid->metaValue<float>("file_voxel_size");
  uint64_t cells=1;
  for (int i=0;i<3;++i) { require(dims[i]>0&&dims[i]<=128,"invalid dimensions"); cells*=dims[i]; }
  require(cells<=2097152 && std::isfinite(voxel)&&voxel>0,"resource or voxel bound");
  require(grid->transform().isLinear(),"nonlinear transform");
  auto origin=grid->transform().indexToWorld(v::Vec3d(0));
  require(origin.length()<1e-12,"nonzero cache transform origin");
  for (int i=0;i<3;++i) {
    v::Vec3d axis(0); axis[i]=1;
    require((grid->transform().indexToWorld(axis)-axis*double(voxel)).length()<1e-12,"transform metadata mismatch");
  }
  std::ostringstream out; out<<std::setprecision(17);
  out<<"{\"name\":"<<safe(grid->getName())<<",\"type\":"<<safe(grid->type())
     <<",\"dimensions\":["<<dims[0]<<','<<dims[1]<<','<<dims[2]<<"],\"voxelSize\":"<<voxel
     <<",\"saveFloatAsHalf\":"<<(grid->saveFloatAsHalf()?"true":"false");
  Hash h;
  if (auto points=v::gridPtrCast<Points>(grid)) {
    std::vector<Row> rows; std::set<std::string> codecs;
    for(auto leaf=points->tree().cbeginLeaf();leaf;++leaf) {
      require(leaf->attributeSet().size()==3,"unexpected point attribute roster");
      const auto& pa=leaf->constAttributeArray("P");
      const auto& va=leaf->constAttributeArray("particles_velocity");
      const auto& fa=leaf->constAttributeArray("U");
      require(pa.stride()==1&&va.stride()==1&&fa.stride()==1,"attribute stride");
      codecs.insert(pa.type().first+":"+pa.type().second);
      codecs.insert(va.type().first+":"+va.type().second);
      codecs.insert(fa.type().first+":"+fa.type().second);
      v::points::AttributeHandle<v::Vec3f> position(pa), velocity(va);
      v::points::AttributeHandle<int> flags(fa);
      for(auto i=leaf->beginIndexAll();i;++i) {
        auto p=position.get(*i);auto vel=velocity.get(*i);auto coord=i.getCoord();
        Row row={double(coord.x())+p.x(),double(coord.y())+p.y(),double(coord.z())+p.z(),vel.x(),vel.y(),vel.z(),double(flags.get(*i))};
        for(double n:row)require(std::isfinite(n),"nonfinite particle");
        rows.push_back(row);require(rows.size()<=2000000,"particle budget");
      }
    }
    require(!rows.empty(),"empty particle roster unsupported by this reader version");
    std::sort(rows.begin(),rows.end());
    for(const auto& row:rows)for(double n:row)h.number(n);
    out<<",\"particleCount\":"<<rows.size()<<",\"attributes\":[\"P\",\"U\",\"particles_velocity\"],\"attributeTypesAndCodecs\":[";
    bool sep=false;for(const auto& codec:codecs){if(sep)out<<',';sep=true;out<<safe(codec);}out<<"],\"sampleRows\":[";
    for(size_t i=0;i<std::min<size_t>(8,rows.size());++i){if(i)out<<',';out<<'[';for(int j=0;j<7;++j){if(j)out<<',';out<<rows[i][j];}out<<']';}out<<']';
  } else if (auto scalar=v::gridPtrCast<v::FloatGrid>(grid)) {
    auto a=scalar->getConstAccessor();uint64_t negative=0,zero=0,positive=0;
    double lo=std::numeric_limits<double>::infinity(),hi=-lo;
    for(int z=0;z<dims[2];++z)for(int y=0;y<dims[1];++y)for(int x=0;x<dims[0];++x){
      double n=a.getValue(v::Coord(x,y,z));h.number(n);lo=std::min(lo,n);hi=std::max(hi,n);
      if(n<0)++negative;else if(n>0)++positive;else ++zero;
    }
    out<<",\"cells\":"<<cells<<",\"negativeCells\":"<<negative<<",\"zeroCells\":"<<zero<<",\"positiveCells\":"<<positive
       <<",\"negativeLevelsetOccupiedVolume\":"<<negative*std::pow(double(voxel),3)<<",\"minimum\":"<<lo<<",\"maximum\":"<<hi;
  } else if (auto vector=v::gridPtrCast<v::Vec3SGrid>(grid)) {
    auto a=vector->getConstAccessor();
    for(int z=0;z<dims[2];++z)for(int y=0;y<dims[1];++y)for(int x=0;x<dims[0];++x){auto n=a.getValue(v::Coord(x,y,z));for(int j=0;j<3;++j)h.number(n[j]);}
    out<<",\"cells\":"<<cells;
  } else if(auto integer=v::gridPtrCast<v::Int32Grid>(grid)) {
    auto a=integer->getConstAccessor();
    for(int z=0;z<dims[2];++z)for(int y=0;y<dims[1];++y)for(int x=0;x<dims[0];++x)h.number(a.getValue(v::Coord(x,y,z)));
    out<<",\"cells\":"<<cells;
  } else throw std::runtime_error("unsupported grid type");
  out<<",\"decodedValueSha256\":\""<<h.finish()<<"\"}";return out.str();
}
void fixtures(const std::string& directory) {
  require(std::filesystem::is_directory(directory)&&std::filesystem::is_empty(directory),"fresh fixture directory required");
  for(const std::string mode:{"base","position","point_velocity","flag","grid_velocity","phi_sign","half","missing_attribute","nonfinite","bad_dimensions","bad_transform"}){
    std::vector<v::Vec3f> p={{.25f,.5f,.75f},{1.f,1.25f,1.5f},{1.75f,1.5f,.25f}};
    if(mode=="position")p[0].x()+=.0625f;
    auto transform=v::math::Transform::createLinearTransform(.25);
    auto points=v::points::createPointDataGrid<v::points::NullCodec,Points>(p,*transform);points->setName("particles");
    v::points::appendAttribute<int>(points->tree(),"U",mode=="flag"?2:1);
    if(mode!="missing_attribute")v::points::appendAttribute<v::Vec3f>(points->tree(),"particles_velocity",v::Vec3f(mode=="point_velocity"?1.25f:1.f,-2,.5f));
    auto phi=v::FloatGrid::create(0);phi->setName("phi");phi->setGridClass(v::GRID_LEVEL_SET);
    phi->tree().fill(v::CoordBBox(v::Coord(0),v::Coord(7)),-2,true);
    phi->tree().fill(v::CoordBBox(v::Coord(8,0,0),v::Coord(15,7,7)),-3,false);
    phi->tree().setValue(v::Coord(15),2);
    if(mode=="phi_sign")phi->tree().setValue(v::Coord(0),2);
    if(mode=="nonfinite")phi->tree().setValue(v::Coord(0),std::numeric_limits<float>::quiet_NaN());
    auto velocity=v::Vec3SGrid::create(v::Vec3f(0));velocity->setName("velocity");
    velocity->tree().setValue(v::Coord(1,2,3),v::Vec3f(mode=="grid_velocity"?2:1,2,3));
    v::GridPtrVec grids={points,phi,velocity};
    for(auto& g:grids){metadata(*g,v::Vec3i(mode=="bad_dimensions"?0:16,16,16),.25f);g->setSaveFloatAsHalf(mode=="half");}
    if(mode=="bad_transform")phi->setTransform(v::math::Transform::createLinearTransform(.5));
    v::io::File file(directory+"/"+mode+".vdb");file.write(grids);file.close();
  }
  std::cout<<"{\"fixtures\":11}\n";
}
int main(int argc,char** argv){
  try {
    v::initialize();
    if(argc==3&&std::string(argv[1])=="--fixtures"){fixtures(argv[2]);return 0;}
    require(argc==2,"one VDB path required");
    require(std::filesystem::is_regular_file(argv[1])&&!std::filesystem::is_symlink(argv[1]),"regular VDB required");
    require(std::filesystem::file_size(argv[1])<=67108864,"file budget");
    v::io::File file(argv[1]);file.open(false);auto grids=file.getGrids();
    require(grids->size()>0&&grids->size()<=16,"grid roster budget");
    std::set<std::string> names;std::vector<std::string> outputs;
    for(auto& g:*grids){require(names.insert(g->getName()).second,"duplicate grid name");outputs.push_back(inspect(g));}
    std::cout<<"{\"readerSchema\":\"bfs.nativeVdb.v1\",\"grids\":[";
    for(size_t i=0;i<outputs.size();++i){if(i)std::cout<<',';std::cout<<outputs[i];}
    std::cout<<"]}\n";file.close();return 0;
  }catch(const std::exception& e){std::cerr<<"NATIVE_VDB_REJECT: "<<e.what()<<'\n';return 2;}
}
