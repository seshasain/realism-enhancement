import os
import random
import sys
import argparse
import tempfile
from typing import Sequence, Mapping, Any, Union
import torch
import gc


def strip_metadata_from_image(image_path: str) -> None:
    """
    Remove ComfyUI metadata and workflow information from saved images.

    Args:
        image_path (str): Path to the image file to clean
    """
    try:
        from PIL import Image

        # Open the image
        with Image.open(image_path) as img:
            # Create a new image without metadata
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(list(img.getdata()))

            # Save the clean image, overwriting the original
            clean_img.save(image_path, format=img.format, optimize=True)
            print(f"[METADATA] Stripped metadata from: {os.path.basename(image_path)}")

    except Exception as e:
        print(f"[METADATA] Warning: Could not strip metadata from {image_path}: {e}")


def clean_output_directory_metadata(output_dir: str, new_files: list) -> None:
    """
    Strip metadata from all newly created files in the output directory.

    Args:
        output_dir (str): Path to the output directory
        new_files (list): List of newly created filenames
    """
    print(f"[METADATA] Cleaning metadata from {len(new_files)} new files...")

    for filename in new_files:
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            file_path = os.path.join(output_dir, filename)
            if os.path.isfile(file_path):
                strip_metadata_from_image(file_path)

    print(f"[METADATA] Metadata cleanup completed")


def get_value_at_index(obj: Union[Sequence, Mapping], index: int) -> Any:
    """Returns the value at the given index of a sequence or mapping.

    If the object is a sequence (like list or string), returns the value at the given index.
    If the object is a mapping (like a dictionary), returns the value at the index-th key.

    Some return a dictionary, in these cases, we look for the "results" key

    Args:
        obj (Union[Sequence, Mapping]): The object to retrieve the value from.
        index (int): The index of the value to retrieve.

    Returns:
        Any: The value at the given index.

    Raises:
        IndexError: If the index is out of bounds for the object and the object is not a mapping.
    """
    try:
        return obj[index]
    except KeyError:
        return obj["result"][index]


def find_path(name: str, path: str = None) -> str:
    """
    Recursively looks at parent folders starting from the given path until it finds the given name.
    Returns the path as a Path object if found, or None otherwise.
    """
    # If no path is given, use the current working directory
    if path is None:
        path = os.getcwd()

    # Check if the current directory contains the name
    if name in os.listdir(path):
        path_name = os.path.join(path, name)
        print(f"{name} found: {path_name}")
        return path_name

    # Get the parent directory
    parent_directory = os.path.dirname(path)

    # If the parent directory is the same as the current directory, we've reached the root and stop the search
    if parent_directory == path:
        return None

    # Recursively call the function with the parent directory
    return find_path(name, parent_directory)


def add_comfyui_directory_to_sys_path() -> None:
    """
    Add 'ComfyUI' to the sys.path
    """
    comfyui_path = find_path("ComfyUI")
    if comfyui_path is not None and os.path.isdir(comfyui_path):
        sys.path.append(comfyui_path)
        print(f"'{comfyui_path}' added to sys.path")


def add_extra_model_paths() -> None:
    """
    Parse the optional extra_model_paths.yaml file and add the parsed paths to the sys.path.
    """
    try:
        from main import load_extra_path_config
    except ImportError:
        try:
            print(
                "Could not import load_extra_path_config from main.py. Looking in utils.extra_config instead."
            )
            from utils.extra_config import load_extra_path_config
        except ImportError:
            print("Could not import load_extra_path_config. ComfyUI may not be available.")
            return

    extra_model_paths = find_path("extra_model_paths.yaml")

    if extra_model_paths is not None:
        load_extra_path_config(extra_model_paths)
    else:
        print("Could not find the extra_model_paths config file.")


add_comfyui_directory_to_sys_path()
add_extra_model_paths()


def import_custom_nodes() -> None:
    """Find all custom nodes in the custom_nodes folder and add those node objects to NODE_CLASS_MAPPINGS

    This function sets up a new asyncio event loop, initializes the PromptServer,
    creates a PromptQueue, and initializes the custom nodes.
    """
    try:
        import asyncio
        import execution
        from nodes import init_extra_nodes
        import server

        # Creating a new event loop and setting it as the default loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Creating an instance of PromptServer with the loop
        server_instance = server.PromptServer(loop)
        execution.PromptQueue(server_instance)

        # Initializing custom nodes
        init_extra_nodes()
    except ImportError as e:
        print(f"ComfyUI modules not available: {e}")
        print("This is expected outside the RunPod environment")


# Import ComfyUI nodes - will be available in RunPod environment
try:
    from nodes import NODE_CLASS_MAPPINGS
except ImportError:
    print("ComfyUI nodes not available - this is expected outside RunPod environment")
    NODE_CLASS_MAPPINGS = {}


def load_image_from_config(image_id: str) -> str:
    """
    Load an image based on the provided image ID using B2 configuration.
    Includes retry logic and fallback to local files if available.

    Args:
        image_id (str): The image identifier/filename to load

    Returns:
        str: Local path to the downloaded image
    """
    import logging
    logger = logging.getLogger("RealSkinAI")
    
    # Create a temporary directory for downloaded images
    temp_dir = tempfile.mkdtemp()
    local_image_path = os.path.join(temp_dir, image_id)

    # First check if the image exists in the input directory
    input_dir = os.path.join(os.getcwd(), "input")
    if not os.path.exists(input_dir):
        os.makedirs(input_dir, exist_ok=True)
        
    local_input_path = os.path.join(input_dir, image_id)
    
    # Check if file exists locally first
    if os.path.exists(local_input_path):
        logger.info(f"Found image locally at {local_input_path}, using local copy")
        
        # Copy to temp dir to maintain consistent behavior
        import shutil
        shutil.copy2(local_input_path, local_image_path)
        logger.info(f"Copied local image to temporary location: {local_image_path}")
        return local_image_path

    # If not found locally, try to download from B2
    logger.info(f"Image not found locally, attempting B2 download for {image_id}")
    
    try:
        # Download the image from B2 using the configuration
        from b2_config import download_file_from_b2, get_b2_config
        
        config = get_b2_config()
        bucket_name = config["B2_IMAGE_BUCKET_NAME"]
        logger.info(f"Downloading {image_id} from B2 bucket {bucket_name}")
        
        # Use the enhanced download function with retry mechanism
        download_file_from_b2(image_id, local_image_path, max_retries=3, retry_delay=2)
        
        # Verify the downloaded file
        if os.path.exists(local_image_path) and os.path.getsize(local_image_path) > 0:
            logger.info(f"Successfully downloaded and verified image: {local_image_path} ({os.path.getsize(local_image_path)} bytes)")
            return local_image_path
        else:
            raise FileNotFoundError(f"Downloaded file is empty or does not exist: {local_image_path}")
            
    except Exception as e:
        logger.error(f"Error downloading image from B2: {str(e)}")
        
        # Check for fallback images in the default directory
        fallback_dir = os.path.join(os.getcwd(), "fallback_images")
        if os.path.exists(fallback_dir):
            # Try to find a suitable fallback image
            fallback_files = os.listdir(fallback_dir)
            if fallback_files:
                fallback_image = fallback_files[0]  # Use first available fallback
                fallback_path = os.path.join(fallback_dir, fallback_image)
                logger.warning(f"Using fallback image: {fallback_path}")
                
                # Copy to the expected location
                import shutil
                shutil.copy2(fallback_path, local_image_path)
                return local_image_path
        
        # If we get here, we couldn't find any suitable fallback
        logger.error("No fallback image available, cannot proceed")
        raise Exception(f"Failed to load image {image_id} and no fallback available: {str(e)}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process images with realism enhancement')
    parser.add_argument('--image-id', type=str, default="1023_mark.jpg",
                       help='Image ID/filename to process (default: ComfyUI_00006_.png)')
    
    # Face parsing parameters
    parser.add_argument('--background', action='store_true', help='Enable background in face parsing')
    parser.add_argument('--skin', action='store_true', help='Enable skin in face parsing')
    parser.add_argument('--nose', action='store_true', default=True, help='Enable nose in face parsing')
    parser.add_argument('--eye-g', action='store_true', default=True, help='Enable eye glasses in face parsing')
    parser.add_argument('--r-eye', action='store_true', default=True, help='Enable right eye in face parsing')
    parser.add_argument('--l-eye', action='store_true', default=True, help='Enable left eye in face parsing')
    parser.add_argument('--r-brow', action='store_true', help='Enable right eyebrow in face parsing')
    parser.add_argument('--l-brow', action='store_true', help='Enable left eyebrow in face parsing')
    parser.add_argument('--r-ear', action='store_true', help='Enable right ear in face parsing')
    parser.add_argument('--l-ear', action='store_true', help='Enable left ear in face parsing')
    parser.add_argument('--mouth', action='store_true', help='Enable mouth in face parsing')
    parser.add_argument('--u-lip', action='store_true', default=True, help='Enable upper lip in face parsing')
    parser.add_argument('--l-lip', action='store_true', default=True, help='Enable lower lip in face parsing')
    parser.add_argument('--hair', action='store_true', help='Enable hair in face parsing')
    parser.add_argument('--hat', action='store_true', help='Enable hat in face parsing')
    parser.add_argument('--ear-r', action='store_true', help='Enable ear ring in face parsing')
    parser.add_argument('--neck-l', action='store_true', help='Enable neck line in face parsing')
    parser.add_argument('--neck', action='store_true', help='Enable neck in face parsing')
    parser.add_argument('--cloth', action='store_true', default=True, help='Enable cloth in face parsing')
    
    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_arguments()
    image_id = args.image_id
    
    # Face parsing parameters
    face_parsing_params = {
        'background': args.background,
        'skin': args.skin,
        'nose': args.nose,
        'eye_g': args.eye_g,
        'r_eye': args.r_eye,
        'l_eye': args.l_eye,
        'r_brow': args.r_brow,
        'l_brow': args.l_brow,
        'r_ear': args.r_ear,
        'l_ear': args.l_ear,
        'mouth': args.mouth,
        'u_lip': args.u_lip,
        'l_lip': args.l_lip,
        'hair': args.hair,
        'hat': args.hat,
        'ear_r': args.ear_r,
        'neck_l': args.neck_l,
        'neck': args.neck,
        'cloth': args.cloth
    }
    
    print(f"[MAIN] Starting main processing for image_id: {image_id}")
    print(f"[MAIN] Face parsing parameters: {face_parsing_params}")
    
    # Check output directory before processing
    output_dir = "/runpod-volume/ComfyUI/output" if os.path.exists("/runpod-volume") else "output"
    
    if os.path.exists(output_dir):
        before_files = os.listdir(output_dir)
        print(f"[MAIN] Output directory before processing: {len(before_files)} files")
    else:
        print(f"[MAIN] Output directory does not exist: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        before_files = []
    
    import_custom_nodes()

    # Load the image using configuration-based approach
    try:
        local_image_path = load_image_from_config(image_id)
        print(f"[MAIN] Downloaded image to: {local_image_path}")

        # Copy the downloaded image to ComfyUI input directory
        input_dir = "/runpod-volume/ComfyUI/input" if os.path.exists("/runpod-volume") else "input"
        image_filename = os.path.basename(local_image_path)
        target_path = os.path.join(input_dir, image_filename)

        # Ensure input directory exists
        os.makedirs(input_dir, exist_ok=True)

        # Copy the file
        import shutil
        shutil.copy2(local_image_path, target_path)
        print(f"[MAIN] Copied image to ComfyUI input: {target_path}")
        print(f"[MAIN] Using image filename: {image_filename}")

    except Exception as e:
        print(f"[MAIN] Error loading image from B2: {e}")
        # Fallback to the original image_id
        image_filename = image_id
        print(f"[MAIN] Using fallback image: {image_filename}")

    with torch.inference_mode():
        loadimage = NODE_CLASS_MAPPINGS["LoadImage"]()
        loadimage_1 = loadimage.load_image(image=image_filename)

        layermask_loadflorence2model = NODE_CLASS_MAPPINGS[
            "LayerMask: LoadFlorence2Model"
        ]()
        layermask_loadflorence2model_3 = layermask_loadflorence2model.load(
            version="large-PromptGen-v2.0"
        )

        checkpointloadersimple = NODE_CLASS_MAPPINGS["CheckpointLoaderSimple"]()
        checkpointloadersimple_7 = checkpointloadersimple.load_checkpoint(
            ckpt_name="epicrealism_naturalSinRC1VAE.safetensors"
        )

        loraloader = NODE_CLASS_MAPPINGS["LoraLoader"]()
        loraloader_8 = loraloader.load_lora(
            lora_name="more_details.safetensors",
            strength_model=1.2,
            strength_clip=1,
            model=get_value_at_index(checkpointloadersimple_7, 0),
            clip=get_value_at_index(checkpointloadersimple_7, 1),
        )

        loraloader_9 = loraloader.load_lora(
            lora_name="SD1.5_epiCRealismHelper (1).safetensors",
            strength_model=1.2,
            strength_clip=1,
            model=get_value_at_index(loraloader_8, 0),
            clip=get_value_at_index(loraloader_8, 1),
        )

        loraloader_10 = loraloader.load_lora(
            lora_name="more_details.safetensors",
            strength_model=1.6000000000000003,
            strength_clip=1,
            model=get_value_at_index(loraloader_9, 0),
            clip=get_value_at_index(loraloader_9, 1),
        )

        layerutility_florence2image2prompt = NODE_CLASS_MAPPINGS[
            "LayerUtility: Florence2Image2Prompt"
        ]()
        layerutility_florence2image2prompt_2 = layerutility_florence2image2prompt.florence2_image2prompt(
            task="more detailed caption",
            text_input="describe the image and great detail, as if you were explaining it to a blind person. Ensure you are focus on every detail of the image including the subject, their clothing, the environment, and finer details about the image itself",
            max_new_tokens=1024,
            num_beams=3,
            do_sample=False,
            fill_mask=False,
            florence2_model=get_value_at_index(layermask_loadflorence2model_3, 0),
            image=get_value_at_index(loadimage_1, 0),
        )

        showtextpysssss = NODE_CLASS_MAPPINGS["ShowText|pysssss"]()
        showtextpysssss_4 = showtextpysssss.notify(
            text=get_value_at_index(layerutility_florence2image2prompt_2, 0),
            unique_id=12610646210403978286,
        )

        cr_combine_prompt = NODE_CLASS_MAPPINGS["CR Combine Prompt"]()
        cr_combine_prompt_5 = cr_combine_prompt.get_value(
            part1=get_value_at_index(showtextpysssss_4, 0),
            part2="and realistic skin texture with visible pores and imperfections, uneven skin tone with natural redness in cheeks, subtle facial hair shadows, fine stubble, natural skin oil on t-zone, fine peach fuzz, naturally occurring blemishes, hyperpigmentation spots, beauty marks, natural sebum, skin texture grain, visible capillaries around nose, subsurface scattering, dermatological realism, fine expression lines, slightly tired under eyes, minor sun damage, asymmetrical features, photorealistic detail, directional studio lighting with slight shadow detail to enhance texture, skin translucency with blue undertones near temples, shot with Sony A7R IV, 85mm f/1.4 portrait lens at f/2.8, color graded in Capture One",
            part3="",
            part4="",
            separator=" ",
        )

        cliptextencode = NODE_CLASS_MAPPINGS["CLIPTextEncode"]()
        cliptextencode_11 = cliptextencode.encode(
            text=get_value_at_index(cr_combine_prompt_5, 0),
            clip=get_value_at_index(loraloader_10, 1),
        )

        cliptextencode_12 = cliptextencode.encode(
            text="(3d, render, cgi, doll, painting, fake, cartoon, 3d modeling:1.4), (worst quality, low quality:1.4), monochrome, deformed, malformed, deformed face, bad teeth, bad hands, bad fingers, bad eyes, long body, blurry, duplicate, cloned, duplicate body parts, disfigured, extra limbs, fused fingers, extra fingers, twisted, distorted, malformed hands, mutated hands and fingers, conjoined, missing limbs, bad anatomy, bad proportions, logo, watermark, text, copyright, signature, lowres, mutated, mutilated, artifacts, gross, ugly, (adult:1.5), (mature features:1.5), plastic skin, doll-like skin, porcelain skin, airbrushed, overly smooth, artificial texture, perfect skin, flat skin, waxy appearance, no pores, digital art skin, uniform coloration, monotone skin, perfectly clean skin, flawless complexion, mannequin skin, perfectly symmetrical features",
            clip=get_value_at_index(loraloader_10, 1),
        )

        vaeencode = NODE_CLASS_MAPPINGS["VAEEncode"]()
        vaeencode_14 = vaeencode.encode(
            pixels=get_value_at_index(loadimage_1, 0),
            vae=get_value_at_index(checkpointloadersimple_7, 2),
        )

        dualcliploader = NODE_CLASS_MAPPINGS["DualCLIPLoader"]()
        dualcliploader_32 = dualcliploader.load_clip(
            clip_name1="clip_l.safetensors",
            clip_name2="t5xxl_fp8_e4m3fn.safetensors",
            type="flux",
            device="default",
        )

        cliptextencode_30 = cliptextencode.encode(
            text="detailed and intricate skin features, 4k, ultra hd, high quality, macro details",
            clip=get_value_at_index(dualcliploader_32, 0),
        )

        unetloadergguf = NODE_CLASS_MAPPINGS["UnetLoaderGGUF"]()
        unetloadergguf_31 = unetloadergguf.load_unet(unet_name="flux1-dev-Q5_0.gguf")

        vaeloader = NODE_CLASS_MAPPINGS["VAELoader"]()
        vaeloader_33 = vaeloader.load_vae(vae_name="flux-fill-vae.safetensors")

        ultralyticsdetectorprovider = NODE_CLASS_MAPPINGS[
            "UltralyticsDetectorProvider"
        ]()
        ultralyticsdetectorprovider_35 = ultralyticsdetectorprovider.doit(
            model_name="segm/face_yolov8m-seg_60.pt"
        )

        faceparsingmodelloaderfaceparsing = NODE_CLASS_MAPPINGS[
            "FaceParsingModelLoader(FaceParsing)"
        ]()
        faceparsingmodelloaderfaceparsing_52 = faceparsingmodelloaderfaceparsing.main(
            device="cuda"
        )

        faceparsingprocessorloaderfaceparsing = NODE_CLASS_MAPPINGS[
            "FaceParsingProcessorLoader(FaceParsing)"
        ]()
        faceparsingprocessorloaderfaceparsing_53 = (
            faceparsingprocessorloaderfaceparsing.main()
        )

        upscalemodelloader = NODE_CLASS_MAPPINGS["UpscaleModelLoader"]()
        upscalemodelloader_188 = upscalemodelloader.load_model(
            model_name="4x_NMKD-Siax_200k.pth"
        )

        layermask_personmaskultra_v2 = NODE_CLASS_MAPPINGS[
            "LayerMask: PersonMaskUltra V2"
        ]()
        masktoimage = NODE_CLASS_MAPPINGS["MaskToImage"]()
        faceparsefaceparsing = NODE_CLASS_MAPPINGS["FaceParse(FaceParsing)"]()
        faceparsingresultsparserfaceparsing = NODE_CLASS_MAPPINGS[
            "FaceParsingResultsParser(FaceParsing)"
        ]()
        growmaskwithblur = NODE_CLASS_MAPPINGS["GrowMaskWithBlur"]()
        combine_masks = NODE_CLASS_MAPPINGS["Combine Masks"]()
        imagetomask = NODE_CLASS_MAPPINGS["ImageToMask"]()
        setlatentnoisemask = NODE_CLASS_MAPPINGS["SetLatentNoiseMask"]()
        ksampler = NODE_CLASS_MAPPINGS["KSampler"]()
        vaedecode = NODE_CLASS_MAPPINGS["VAEDecode"]()
        image_comparer_rgthree = NODE_CLASS_MAPPINGS["Image Comparer (rgthree)"]()
        fluxguidance = NODE_CLASS_MAPPINGS["FluxGuidance"]()
        facedetailer = NODE_CLASS_MAPPINGS["FaceDetailer"]()
        imagecompositemasked = NODE_CLASS_MAPPINGS["ImageCompositeMasked"]()
        cr_simple_image_compare = NODE_CLASS_MAPPINGS["CR Simple Image Compare"]()
        get_image_size = NODE_CLASS_MAPPINGS["Get Image Size"]()
        imageupscalewithmodel = NODE_CLASS_MAPPINGS["ImageUpscaleWithModel"]()
        imagescaleby = NODE_CLASS_MAPPINGS["ImageScaleBy"]()
        getimagesize = NODE_CLASS_MAPPINGS["GetImageSize+"]()
        imageresizekjv2 = NODE_CLASS_MAPPINGS["ImageResizeKJv2"]()
        saveimage = NODE_CLASS_MAPPINGS["SaveImage"]()

        for q in range(1):
            layermask_personmaskultra_v2_64 = (
                layermask_personmaskultra_v2.person_mask_ultra_v2(
                    face=True,
                    hair=True,
                    body=True,
                    clothes=False,
                    accessories=False,
                    background=False,
                    confidence=0.20000000000000004,
                    detail_method="VITMatte(local)",
                    detail_erode=6,
                    detail_dilate=6,
                    black_point=0.010000000000000002,
                    white_point=0.99,
                    process_detail=True,
                    device="cuda",
                    max_megapixels=2,
                    images=get_value_at_index(loadimage_1, 0),
                )
            )

            masktoimage_62 = masktoimage.mask_to_image(
                mask=get_value_at_index(layermask_personmaskultra_v2_64, 1)
            )

            faceparsefaceparsing_54 = faceparsefaceparsing.main(
                model=get_value_at_index(faceparsingmodelloaderfaceparsing_52, 0),
                processor=get_value_at_index(
                    faceparsingprocessorloaderfaceparsing_53, 0
                ),
                image=get_value_at_index(loadimage_1, 0),
            )

            faceparsingresultsparserfaceparsing_55 = (
                faceparsingresultsparserfaceparsing.main(
                background=face_parsing_params['background'],
                skin=face_parsing_params['skin'],
                nose=face_parsing_params['nose'],
                eye_g=face_parsing_params['eye_g'],
                r_eye=face_parsing_params['r_eye'],
                l_eye=face_parsing_params['l_eye'],
                r_brow=face_parsing_params['r_brow'],
                l_brow=face_parsing_params['l_brow'],
                r_ear=face_parsing_params['r_ear'],
                l_ear=face_parsing_params['l_ear'],
                mouth=face_parsing_params['mouth'],
                u_lip=face_parsing_params['u_lip'],
                l_lip=face_parsing_params['l_lip'],
                hair=face_parsing_params['hair'],
                hat=face_parsing_params['hat'],
                ear_r=face_parsing_params['ear_r'],
                neck_l=face_parsing_params['neck_l'],
                neck=face_parsing_params['neck'],
                cloth=face_parsing_params['cloth'],
                result=get_value_at_index(faceparsefaceparsing_54, 1),
            )
        )

            growmaskwithblur_68 = growmaskwithblur.expand_mask(
                expand=15,
                incremental_expandrate=0,
                tapered_corners=True,
                flip_input=False,
                blur_radius=4,
                lerp_alpha=1,
                decay_factor=1,
                fill_holes=False,
                mask=get_value_at_index(faceparsingresultsparserfaceparsing_55, 0),
            )

            masktoimage_56 = masktoimage.mask_to_image(
                mask=get_value_at_index(growmaskwithblur_68, 0)
            )

            combine_masks_59 = combine_masks.combine(
                op="difference",
                clamp_result="yes",
                round_result="no",
                image1=get_value_at_index(masktoimage_62, 0),
                image2=get_value_at_index(masktoimage_56, 0),
            )

            imagetomask_60 = imagetomask.image_to_mask(
                channel="red", image=get_value_at_index(combine_masks_59, 0)
            )

            setlatentnoisemask_15 = setlatentnoisemask.set_mask(
                samples=get_value_at_index(vaeencode_14, 0),
                mask=get_value_at_index(imagetomask_60, 0),
            )

            ksampler_6 = ksampler.sample(
                seed=random.randint(1, 2**64),
                steps=40,
                cfg=6,
                sampler_name="dpmpp_2m_sde",
                scheduler="karras",
                denoise=0.30000000000000004,
                model=get_value_at_index(checkpointloadersimple_7, 0),
                positive=get_value_at_index(cliptextencode_11, 0),
                negative=get_value_at_index(cliptextencode_12, 0),
                latent_image=get_value_at_index(setlatentnoisemask_15, 0),
            )

            vaedecode_13 = vaedecode.decode(
                samples=get_value_at_index(ksampler_6, 0),
                vae=get_value_at_index(checkpointloadersimple_7, 2),
            )

            image_comparer_rgthree_27 = image_comparer_rgthree.compare_images(
                image_a=get_value_at_index(loadimage_1, 0),
                image_b=get_value_at_index(vaedecode_13, 0),
            )

            fluxguidance_34 = fluxguidance.append(
                guidance=3.5, conditioning=get_value_at_index(cliptextencode_30, 0)
            )

            facedetailer_29 = facedetailer.doit(
                guide_size=512,
                guide_size_for=True,
                max_size=1024,
                seed=random.randint(1, 2**64),
                steps=20,
                cfg=3,
                sampler_name="euler",
                scheduler="normal",
                denoise=0.12000000000000002,
                feather=5,
                noise_mask=True,
                force_inpaint=True,
                bbox_threshold=0.5,
                bbox_dilation=10,
                bbox_crop_factor=3,
                sam_detection_hint="center-1",
                sam_dilation=0,
                sam_threshold=0.93,
                sam_bbox_expansion=0,
                sam_mask_hint_threshold=0.7,
                sam_mask_hint_use_negative="False",
                drop_size=10,
                wildcard="",
                cycle=1,
                inpaint_model=False,
                noise_mask_feather=20,
                tiled_encode=False,
                tiled_decode=False,
                image=get_value_at_index(vaedecode_13, 0),
                model=get_value_at_index(unetloadergguf_31, 0),
                clip=get_value_at_index(dualcliploader_32, 0),
                vae=get_value_at_index(vaeloader_33, 0),
                positive=get_value_at_index(fluxguidance_34, 0),
                negative=get_value_at_index(cliptextencode_30, 0),
                bbox_detector=get_value_at_index(ultralyticsdetectorprovider_35, 0),
            )

            imagecompositemasked_65 = imagecompositemasked.composite(
                x=0,
                y=0,
                resize_source=False,
                destination=get_value_at_index(loadimage_1, 0),
                source=get_value_at_index(vaedecode_13, 0),
                mask=get_value_at_index(imagetomask_60, 0),
            )

            image_comparer_rgthree_67 = image_comparer_rgthree.compare_images(
                image_a=get_value_at_index(loadimage_1, 0),
                image_b=get_value_at_index(imagecompositemasked_65, 0),
            )

            imagecompositemasked_70 = imagecompositemasked.composite(
                x=0,
                y=0,
                resize_source=False,
                destination=get_value_at_index(loadimage_1, 0),
                source=get_value_at_index(facedetailer_29, 0),
                mask=get_value_at_index(imagetomask_60, 0),
            )

            image_comparer_rgthree_71 = image_comparer_rgthree.compare_images(
                image_a=get_value_at_index(loadimage_1, 0),
                image_b=get_value_at_index(facedetailer_29, 0),
            )

            image_comparer_rgthree_73 = image_comparer_rgthree.compare_images(
                image_a=get_value_at_index(loadimage_1, 0),
                image_b=get_value_at_index(imagecompositemasked_70, 0),
            )

            cr_simple_image_compare_74 = cr_simple_image_compare.layout(
                text1="BEFORE",
                text2="AFTER",
                footer_height=100,
                font_name="impact.ttf",
                font_size=50,
                mode="dark",
                border_thickness=20,
                image1=get_value_at_index(loadimage_1, 0),
                image2=get_value_at_index(facedetailer_29, 0),
            )

            get_image_size_186 = get_image_size.get_size(
                image=get_value_at_index(loadimage_1, 0)
            )

            imageupscalewithmodel_189 = imageupscalewithmodel.upscale(
                upscale_model=get_value_at_index(upscalemodelloader_188, 0),
                image=get_value_at_index(loadimage_1, 0),
            )

            imagescaleby_190 = imagescaleby.upscale(
                upscale_method="nearest-exact",
                scale_by=0.5000000000000001,
                image=get_value_at_index(imageupscalewithmodel_189, 0),
            )

            getimagesize_192 = getimagesize.execute(
                image=get_value_at_index(loadimage_1, 0)
            )

            imageresizekjv2_191 = imageresizekjv2.resize(
                width=get_value_at_index(getimagesize_192, 0),
                height=get_value_at_index(getimagesize_192, 1),
                upscale_method="nearest-exact",
                keep_proportion="resize",
                pad_color="0, 0, 0",
                crop_position="center",
                divisible_by=2,
                device="gpu",
                image=get_value_at_index(imagescaleby_190, 0),
            )

            image_comparer_rgthree_193 = image_comparer_rgthree.compare_images(
                image_a=get_value_at_index(loadimage_1, 0),
                image_b=get_value_at_index(imageresizekjv2_191, 0),
            )

            saveimage_202 = saveimage.save_images(
                filename_prefix="RealSkin AI Lite Comparer Original Vs Final",
                images=get_value_at_index(cr_simple_image_compare_74, 0),
            )

            # Save the final AI-enhanced image
            saveimage_final = saveimage.save_images(
                filename_prefix="RealSkin AI Final Output",
                images=get_value_at_index(facedetailer_29, 0),
            )

    # Check output directory after processing
    if os.path.exists(output_dir):
        after_files = os.listdir(output_dir)
        print(f"[MAIN] Output directory after processing: {len(after_files)} files")
        new_files = set(after_files) - set(before_files)
        if new_files:
            print(f"[MAIN] New files created: {sorted(new_files)}")
            for file in sorted(new_files):
                file_path = os.path.join(output_dir, file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    print(f"[MAIN]   - {file} ({size} bytes)")

            # Strip ComfyUI metadata from all new image files
            clean_output_directory_metadata(output_dir, list(new_files))
        else:
            print(f"[MAIN] No new files detected!")
    else:
        print(f"[MAIN] Output directory still does not exist: {output_dir}")

    # Final cleanup
    print(f"[MAIN] Starting final cleanup...")
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        gc.collect()
        print(f"[MAIN] Final cleanup completed")
    except Exception as e:
        print(f"[MAIN] Cleanup warning: {e}")

    print(f"[MAIN] Main processing completed for image_id: {image_id}")

    # Return paths to output files
    comparison_files = [f for f in new_files if "Comparer" in f]
    comparison_path = os.path.join(output_dir, comparison_files[0]) if comparison_files else None
    
    final_ai_files = [f for f in new_files if "Final Output" in f]
    final_ai_path = os.path.join(output_dir, final_ai_files[0]) if final_ai_files else None

    return {
        "status": "success",
        "message": f"Successfully processed image: {image_id}",
        "outputs": {
            "comparison_image": comparison_path,
            "final_ai_image": final_ai_path,
        }
    }


def runpod_handler(job):
    """
    RunPod serverless handler function.

    Expected input format:
    {
        "input": {
            "image_id": "image_filename.jpg",  # Optional
            "face_parsing": {                  # Optional face parsing parameters
                "background": false,
                "skin": false,
                "nose": true,
                "eye_g": true,
                "r_eye": true,
                "l_eye": true,
                "r_brow": false,
                "l_brow": false,
                "r_ear": false,
                "l_ear": false,
                "mouth": false,
                "u_lip": true,
                "l_lip": true,
                "hair": false,
                "hat": false,
                "ear_r": false,
                "neck_l": false,
                "neck": false,
                "cloth": true
            }
        }
    }

    Returns:
    {
        "status": "success" | "error",
        "message": "Success/error message",
        "outputs": {
            "comparison_image": "path_to_comparison_image"
        }
    }
    """
    import traceback
    import logging
    import time
    import sys
    import json
    import os
    import shutil
    from datetime import datetime

    # Set up detailed logging
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format)
    logger = logging.getLogger("RealSkinAI")
    
    # Add file handler for persistent logs
    try:
        log_dir = "/runpod-volume/logs"
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(f"{log_dir}/handler-{int(time.time())}.log")
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to set up file logging: {str(e)}")
    
    # Log system info
    logger.info("=== RUNPOD HANDLER EXECUTION START ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Execution timestamp: {datetime.now().isoformat()}")
    logger.info(f"Job ID: {job.get('id', 'unknown')}")

    # Log CUDA availability if torch is available
    try:
        import torch
        logger.info(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"CUDA device: {torch.cuda.get_device_name(0)}")
            logger.info(f"CUDA memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    except ImportError:
        logger.warning("PyTorch not available, skipping CUDA check")

    try:
        # Log the input parameters (sanitized)
        input_data = job.get("input", {})
        sanitized_input = input_data.copy()
        logger.info(f"Job input received: {json.dumps(sanitized_input)}")
        
        # Extract and validate image_id
        image_id = input_data.get("image_id")
        if not image_id:
            image_id = "1023_mark.jpg"  # Default image
            logger.info(f"No image_id provided, using default: {image_id}")
        else:
            logger.info(f"Processing image: {image_id}")
        
        # Check if the image already exists in the input directory
        input_dir = "/runpod-volume/ComfyUI/input" if os.path.exists("/runpod-volume") else "input"
        if not os.path.exists(input_dir):
            logger.info(f"Creating input directory: {input_dir}")
            os.makedirs(input_dir, exist_ok=True)
        
        # Check if the image exists in the input directory
        image_path = os.path.join(input_dir, image_id)
        if os.path.exists(image_path):
            logger.info(f"Image already exists in input directory: {image_path}")
        else:
            logger.info(f"Image not found in input directory: {image_path}")
            
            # Check if we have a fallback image
            fallback_dir = "/runpod-volume/ComfyUI/fallback_images" if os.path.exists("/runpod-volume") else "fallback_images"
            if os.path.exists(fallback_dir):
                fallback_files = os.listdir(fallback_dir)
                if fallback_files:
                    logger.info(f"Found fallback images: {fallback_files}")
                    fallback_image = os.path.join(fallback_dir, fallback_files[0])
                    logger.info(f"Using fallback image: {fallback_image}")
                    shutil.copy2(fallback_image, image_path)
                    logger.info(f"Copied fallback image to input directory: {image_path}")
        
        # Extract face parsing parameters with defaults
        face_parsing = input_data.get("face_parsing", {})
        face_parsing_params = {
            'background': face_parsing.get('background', False),
            'skin': face_parsing.get('skin', False),
            'nose': face_parsing.get('nose', True),
            'eye_g': face_parsing.get('eye_g', True),
            'r_eye': face_parsing.get('r_eye', True),
            'l_eye': face_parsing.get('l_eye', True),
            'r_brow': face_parsing.get('r_brow', False),
            'l_brow': face_parsing.get('l_brow', False),
            'r_ear': face_parsing.get('r_ear', False),
            'l_ear': face_parsing.get('l_ear', False),
            'mouth': face_parsing.get('mouth', False),
            'u_lip': face_parsing.get('u_lip', True),
            'l_lip': face_parsing.get('l_lip', True),
            'hair': face_parsing.get('hair', False),
            'hat': face_parsing.get('hat', False),
            'ear_r': face_parsing.get('ear_r', False),
            'neck_l': face_parsing.get('neck_l', False),
            'neck': face_parsing.get('neck', False),
            'cloth': face_parsing.get('cloth', True)
        }
        
        logger.info(f"Face parsing parameters: {face_parsing_params}")
        
        # Create Args object to pass to main
        class Args:
            pass
        
        args = Args()
        args.image_id = image_id
        for param, value in face_parsing_params.items():
            setattr(args, param, value)
        
        # Override parse_arguments globally with a function that returns our args
        global parse_arguments
        original_parse_arguments = parse_arguments
        parse_arguments = lambda: args
        
        # Check output directory before processing
        output_dir = "/runpod-volume/ComfyUI/output" if os.path.exists("/runpod-volume") else "output"
        if not os.path.exists(output_dir):
            logger.info(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        else:
            before_files = os.listdir(output_dir)
            logger.info(f"Output directory before processing: {len(before_files)} files")
            
        try:
            # Call the main function which will use our custom parse_arguments
            logger.info("Starting main processing function")
            start_time = time.time()
            
            # Import custom nodes
            try:
                logger.info("Importing custom nodes")
                import_custom_nodes()
                logger.info("Custom nodes imported successfully")
            except Exception as e:
                logger.error(f"Error importing custom nodes: {str(e)}")
                logger.error(traceback.format_exc())
            
            # Call main function with detailed progress logging
            logger.info("Calling main() function")
            result = main()
            processing_time = time.time() - start_time
            logger.info(f"Main processing completed in {processing_time:.2f} seconds")
            
            # Check output directory after processing
            if os.path.exists(output_dir):
                after_files = os.listdir(output_dir)
                new_files = [f for f in after_files if f not in before_files]
                logger.info(f"Output directory after processing: {len(after_files)} files")
                logger.info(f"New files created: {len(new_files)}")
                logger.info(f"New files: {new_files}")
                
                # Add new files to result
                if "outputs" not in result:
                    result["outputs"] = {}
                result["outputs"]["generated_files"] = new_files
        finally:
            # Restore the original function
            parse_arguments = original_parse_arguments
        
        # Handle B2 storage upload with fallback mechanism
        try:
            from b2_config import upload_file_to_b2
                
            uploaded_outputs = {}
            if "outputs" in result and result["outputs"].get("final_ai_image"):
                file_path = result["outputs"]["final_ai_image"]
                
                if file_path and os.path.exists(file_path):
                    filename = os.path.basename(file_path)
                    timestamp = int(time.time())
                    b2_filename = f"realskin_output_{timestamp}_{filename}"

                    logger.info(f"Uploading final AI image ({file_path}) as {b2_filename}...")
                    
                    # Try to upload with retries
                    max_retries = 3
                    retry_count = 0
                    
                    while retry_count < max_retries:
                        try:
                            b2_url = upload_file_to_b2(file_path, b2_filename)
                            uploaded_outputs['final_ai_image'] = {
                                "local_path": file_path,
                                "b2_url": b2_url,
                                "b2_filename": b2_filename
                            }
                            logger.info(f"Successfully uploaded to B2: {b2_url}")
                            break
                        except Exception as upload_error:
                            retry_count += 1
                            if retry_count < max_retries:
                                retry_delay = 2 * retry_count
                                logger.warning(f"Upload attempt {retry_count} failed: {str(upload_error)}. Retrying in {retry_delay}s...")
                                time.sleep(retry_delay)
                            else:
                                logger.error(f"All upload attempts failed: {str(upload_error)}")
                                result["b2_upload_error"] = str(upload_error)
            
                result["b2_uploads"] = uploaded_outputs
        except Exception as e:
            logger.error(f"Error during B2 upload: {str(e)}")
            logger.error(traceback.format_exc())
            result["b2_upload_error"] = str(e)
        
        # Log success and return result
        logger.info("Handler execution completed successfully")
        return result

    except Exception as e:
        error_msg = f"Error processing image: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # Attempt to clean up any temporary files
        try:
            import tempfile
            import shutil
            temp_dirs = [d for d in os.listdir(tempfile.gettempdir()) if d.startswith('tmp')]
            for d in temp_dirs:
                try:
                    shutil.rmtree(os.path.join(tempfile.gettempdir(), d))
                except:
                    pass
            logger.info("Temporary file cleanup attempted")
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {str(cleanup_error)}")

        return {
            "status": "error",
            "message": error_msg,
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    main()
