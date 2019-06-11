from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point


from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import status

from .serializers import WallsSerializer, CommentsSerializer, WallSerializer

from .models import Wall, Comment


class CreateWall(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        name = request.data.get("name", None)
        lat = request.data.get("lat", None)
        lng = request.data.get("lng", None)
        pnt = Point(lng, lat, srid=4326) if lat and lng else None
        comment = request.data.get("comment", None)
        try:
            name = null if name == "" else name
            near = False
            walls = Wall.order_by_dist(pnt)
            if len(walls) == 0:
                wall = Wall.objects.create(
                    name=name,
                    lat=lat,
                    lng=lng,
                )
            else:
                for w in walls:
                    near = True if pnt and w.point.distance(pnt) >= 0.0015 else near
                    if near:
                        break
                    elif w == walls[-1]:
                        wall = Wall.objects.create(
                            name=name,
                            lat=lat,
                            lng=lng,
                        )
                        breakpoint()
                    else:
                        continue

            comment = wall.comment_set.create(
                comment = request.data.get("comment", "")
            )

            return Response(data=WallSerializer(wall).data, status=status.HTTP_201_CREATED)
        except NameError:
            return Response(data={
                "error": "Too close to another wall to create at your current location."
            }, status=status.HTTP_409_CONFLICT)
        except django.db.utils.IntegrityError:
            return Response(data={
                "error": "Fields missing, could not save wall."
            }, status=status.HTTP_409_CONFLICT)

class WallIndex(generics.ListAPIView):

    def get(self, request, **kwargs):
        try:
            lat = float(request.query_params['lat'])
            lng = float(request.query_params['lng'])
            pnt = Point(lng, lat, srid=4326)
            walls = {}
            for wall in Wall.objects.annotate(distance=Distance('point', pnt)):
                walls[wall.distance.m] = wall
            dists = []
            for i in walls.keys(): dists.append(i)
            sorted_dists = sorted(dists)
            closest_walls = []
            for i in sorted_dists: closest_walls.append(walls[i])
            walls = []
            for wall in closest_walls[0:5]:
                walls.append(WallsSerializer(wall).data)
            return Response(data=walls, status=status.HTTP_200_OK)
        except:
            return Response(data= {"error": "Cannot Locate Nearest Walls"}, status=status.HTTP_404_NOT_FOUND)


class WallShow(generics.RetrieveAPIView):

    def get(self, request, **kwargs):
        try:
            wall = Wall.objects.get(pk=kwargs['pk'])
            return Response(data= WallSerializer(wall).data, status=status.HTTP_200_OK)
        except (KeyError, Wall.DoesNotExist):
            return Response(data= {"error": "Could Not Find Wall"}, status=status.HTTP_404_NOT_FOUND)

class CreateComment(generics.CreateAPIView):
    serializer_class = CommentsSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, **kwargs):
        comment = request.data.get("comment", "")
        try:
            wall = Wall.objects.get(pk=kwargs['pk'])
            Comment.objects.create(
                wall = wall,
                comment = comment
            )
            return Response(data={"message": "Comment Saved!"}, status=status.HTTP_201_CREATED)
        except (KeyError, Wall.DoesNotExist):
            return Response(data={"error": "Conflict!"}, status=status.HTTP_409_CONFLICT)
