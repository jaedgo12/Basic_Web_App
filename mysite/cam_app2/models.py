from django.db import models
from django.shortcuts import render
from django.conf import settings
from django import forms

from modelcluster.fields import ParentalKey

from wagtail.admin.panels import (
    FieldPanel,
    MultiFieldPanel,
)
from wagtail.models import Page
from wagtail.fields import RichTextField
from django.core.files.storage import default_storage

from pathlib import Path


import os, uuid, glob, cv2, torch

str_uuid = uuid.uuid4()  # The UUID for image uploading

def reset():
    files_result = glob.glob(str(Path(f'{settings.MEDIA_ROOT}/Result/*.*')), recursive=True)
    files_upload = glob.glob(str(Path(f'{settings.MEDIA_ROOT}/uploadedPics/*.*')), recursive=True)
    files = []
    if len(files_result) != 0:
        files.extend(files_result)
    if len(files_upload) != 0:
        files.extend(files_upload)
    if len(files) != 0:
        for f in files:
            try:
                if (not (f.endswith(".txt"))):
                    os.remove(f)
            except OSError as e:
                print("Error: %s : %s" % (f, e.strerror))
        file_li = [Path(f'{settings.MEDIA_ROOT}/Result/Result.txt'),
                   Path(f'{settings.MEDIA_ROOT}/uploadedPics/img_list.txt'),
                   Path(f'{settings.MEDIA_ROOT}/Result/stats.txt')]
        for p in file_li:
            file = open(Path(p), "r+")
            file.truncate(0)
            file.close()

# Create your models here.
class ImagePage(Page):
    """Image Page."""

    template = "cam_app2/image.html"

    max_count = 2

    name_title = models.CharField(max_length=100, blank=True, null=True)
    name_subtitle = RichTextField(features=["bold", "italic"], blank=True)

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("name_title"),
                FieldPanel("name_subtitle"),

            ],
            heading="Page Options",
        ),
    ]


    def reset_context(self, request):
        context = super().get_context(request)
        context["my_uploaded_file_names"]= []
        context["my_result_file_names"]=[]
        context["my_staticSet_names"]= []
        context["my_lines"]= []
        return context

    def serve(self, request):
        emptyButtonFlag = False
        if request.POST.get('start')=="":


            ##on start button press,

            model_path = os.path.join(settings.BASE_DIR, "deep_learning_models/best.pt")
            self.model = torch.hub.load(
            "ultralytics/yolov5", "custom", path=model_path, force_reload=False
            )

            context = self.reset_context(request)
            print(request.POST.get('start'))
            print("Start selected")
            fileroot = os.path.join(settings.MEDIA_ROOT, 'uploadedPics')
            res_f_root = os.path.join(settings.MEDIA_ROOT, 'Result')
            with open(Path(f'{settings.MEDIA_ROOT}/uploadedPics/img_list.txt'), 'r') as f:
                image_files = f.readlines()
            if len(image_files)>=0:
                for file in image_files:
                    ###
                    # For each file, read, pass to model, do something, save it #
                    ###
                    print('file',file)
                    filename = file.split('\\')[-1]
                    filepath = os.path.join(fileroot, filename)
                    print('fileroot',fileroot)
                    print('filename',filename)
                    print('filepath',filepath)
                    print('filepath stripped',filepath.strip())
                    img = cv2.imread(filepath.strip())




                    # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    # fn = filename.split('.')[:-1][0]
                    # r_filename = f'result_{fn}.jpeg'
                    # print(r_filename)
                    # cv2.imwrite(str(os.path.join(res_f_root, r_filename)), gray)

                    # Perform YOLOv5 detection
                    results = self.model(img)

                    # Draw bounding boxes and labels on the image
                    for detection in results.xyxy[0]:  # Assuming a single image in the batch
                        x1, y1, x2, y2 = map(int, detection[:4])
                        conf = detection[4]
                        cls = int(detection[5])
                        # label = f"{self.model.names[cls]} {conf:.2f}"


                        if conf >= 0 and conf < 0.3:
                            conf_label = 'Conf: Low'
                        elif conf >= 0.3 and conf < 0.6:
                            conf_label = 'Conf: Medium'
                        else:
                            conf_label = 'Conf: High'


                        label = f"{self.model.names[cls]} {conf_label}"
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(
                            img,
                            label,
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.9,
                            (0, 255, 0),
                            2,
                        )


                    # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    fn = filename.split('.')[:-1][0]
                    r_filename = f'result_{fn}.jpeg'
                    print(r_filename)
                    cv2.imwrite(str(os.path.join(res_f_root, r_filename)), img)






                    r_media_filepath = Path(f"{settings.MEDIA_URL}Result/{r_filename}")
                    print(r_media_filepath)
                    with open(Path(f'{settings.MEDIA_ROOT}/Result/Result.txt'), 'a') as f:
                        f.write(str(r_media_filepath))
                        f.write("\n")
                    context["my_uploaded_file_names"].append(str(f'{str(file)}'))
                    context["my_result_file_names"].append(str(f'{str(r_media_filepath)}'))
            return render(request, "cam_app2/image.html", context)

        if (request.FILES and emptyButtonFlag == False):
            print("reached here files")
            reset()
            context = self.reset_context(request)
            context["my_uploaded_file_names"] = []
            for file_obj in request.FILES.getlist("file_data"):
                uuidStr = uuid.uuid4()
                filename = f"{file_obj.name.split('.')[0]}_{uuidStr}.{file_obj.name.split('.')[-1]}"
                with default_storage.open(Path(f"uploadedPics/{filename}"), 'wb+') as destination:
                    for chunk in file_obj.chunks():
                        destination.write(chunk)
                filename = Path(f"{settings.MEDIA_URL}uploadedPics/{file_obj.name.split('.')[0]}_{uuidStr}.{file_obj.name.split('.')[-1]}")
                with open(Path(f'{settings.MEDIA_ROOT}/uploadedPics/img_list.txt'), 'a') as f:
                    f.write(str(filename))
                    f.write("\n")

                context["my_uploaded_file_names"].append(str(f'{str(filename)}'))
            return render(request, "cam_app2/image.html", context)
        context = self.reset_context(request)
        reset()
        return render(request, "cam_app2/image.html", {'page': self})
