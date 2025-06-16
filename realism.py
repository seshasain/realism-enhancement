import os
import random
import sys
import argparse
import tempfile
from typing import Sequence, Mapping, Any, Union
import torch
from b2_config import get_b2_config, download_file_from_b2


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

    Args:
        image_id (str): The image identifier/filename to load

    Returns:
        str: Local path to the downloaded image
    """
    # Create a temporary directory for downloaded images
    temp_dir = tempfile.mkdtemp()
    local_image_path = os.path.join(temp_dir, image_id)

    try:
        # Download the image from B2 using the configuration
        download_file_from_b2(image_id, local_image_path)
        print(f"Successfully downloaded image: {image_id} to {local_image_path}")
        return local_image_path
    except Exception as e:
        print(f"Failed to download image {image_id}: {e}")
        # Fallback to local file if it exists
        if os.path.exists(image_id):
            print(f"Using local file: {image_id}")
            return image_id
        else:
            raise FileNotFoundError(f"Could not find image {image_id} locally or in B2 storage")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process images with realism enhancement')
    parser.add_argument('--image-id', type=str, default="Asian+Man+1+Before.jpg",
                       help='Image ID/filename to process (default: Asian+Man+1+Before.jpg)')
    return parser.parse_args()


def main(image_id: str = "Asian+Man+1+Before.jpg",
         detail_amount: float = 0.7,
         denoise_strength: float = 0.3,
         cfg_scale: int = 6,
         upscale_factor: float = 2.0,
         steps: int = 40,
         lora_strength: float = 1.2,
         # Face Enhancement Parameters
         enhance_eyes: bool = True,
         enhance_skin: bool = True,
         enhance_hair: bool = True,
         enhance_lips: bool = True,
         enhance_teeth: bool = True,
         # Facial Area Enhancement Parameters
         enhance_cheeks: bool = True,
         enhance_forehead: bool = True,
         enhance_nose: bool = True,
         enhance_jawline: bool = True,
         # Feature Strength Parameters
         eye_enhancement: float = 0.8,
         skin_smoothing: float = 0.6,
         hair_detail: float = 0.7,
         lip_enhancement: float = 0.5,
         teeth_whitening: float = 0.4,
         # Facial Area Strength Parameters
         cheek_enhancement: float = 0.6,
         forehead_smoothing: float = 0.5,
         nose_refinement: float = 0.4,
         jawline_definition: float = 0.5,
         # Overall Enhancement Parameters
         enhance_lighting: bool = True,
         enhance_shadows: bool = True,
         enhance_highlights: bool = True,
         color_correction: float = 0.5,
         contrast_boost: float = 0.3,
         # Object/Product Protection Parameters
         protect_objects: bool = True,
         protect_hands: bool = True,
         protect_clothing: bool = True,
         face_only_mode: bool = False):
    import gc
    print(f"[MAIN] Starting main processing for image_id: {image_id}")
    print(f"[MAIN] Enhancement parameters:")
    print(f"  - Detail Amount: {detail_amount}")
    print(f"  - Denoise Strength: {denoise_strength}")
    print(f"  - CFG Scale: {cfg_scale}")
    print(f"  - Upscale Factor: {upscale_factor}")
    print(f"  - Steps: {steps}")
    print(f"  - LoRA Strength: {lora_strength}")
    print(f"[MAIN] Face Enhancement Features:")
    print(f"  - Enhance Eyes: {enhance_eyes} (strength: {eye_enhancement})")
    print(f"  - Enhance Skin: {enhance_skin} (smoothing: {skin_smoothing})")
    print(f"  - Enhance Hair: {enhance_hair} (detail: {hair_detail})")
    print(f"  - Enhance Lips: {enhance_lips} (enhancement: {lip_enhancement})")
    print(f"  - Enhance Teeth: {enhance_teeth} (whitening: {teeth_whitening})")
    print(f"[MAIN] Facial Area Enhancement Features:")
    print(f"  - Enhance Cheeks: {enhance_cheeks} (enhancement: {cheek_enhancement})")
    print(f"  - Enhance Forehead: {enhance_forehead} (smoothing: {forehead_smoothing})")
    print(f"  - Enhance Nose: {enhance_nose} (refinement: {nose_refinement})")
    print(f"  - Enhance Jawline: {enhance_jawline} (definition: {jawline_definition})")
    print(f"[MAIN] Overall Enhancement Features:")
    print(f"  - Enhance Lighting: {enhance_lighting}")
    print(f"  - Enhance Shadows: {enhance_shadows}")
    print(f"  - Enhance Highlights: {enhance_highlights}")
    print(f"  - Color Correction: {color_correction}")
    print(f"  - Contrast Boost: {contrast_boost}")
    print(f"[MAIN] Object Protection Features:")
    print(f"  - Protect Objects/Products: {protect_objects}")
    print(f"  - Protect Hands: {protect_hands}")
    print(f"  - Protect Clothing: {protect_clothing}")
    print(f"  - Face Only Mode: {face_only_mode}")
    import_custom_nodes()

    # Load the image using configuration-based approach
    try:
        local_image_path = load_image_from_config(image_id)
        print(f"[MAIN] Downloaded image to: {local_image_path}")

        # Copy the downloaded image to ComfyUI input directory
        input_dir = "/runpod-volume/ComfyUI/input"
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
        # Fallback to the original hardcoded image or use the provided image_id directly
        image_filename = image_id
        print(f"[MAIN] Using fallback image: {image_filename}")

    # Check output directory before processing
    output_dir = "/runpod-volume/ComfyUI/output"
    if os.path.exists(output_dir):
        before_files = os.listdir(output_dir)
        print(f"[MAIN] Output directory before processing: {len(before_files)} files")
    else:
        print(f"[MAIN] Output directory does not exist: {output_dir}")
        before_files = []

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
            lora_name="more_details (1).safetensors",
            strength_model=lora_strength,
            strength_clip=1,
            model=get_value_at_index(checkpointloadersimple_7, 0),
            clip=get_value_at_index(checkpointloadersimple_7, 1),
        )

        loraloader_9 = loraloader.load_lora(
            lora_name="SD1.5_epiCRealismHelper (1).safetensors",
            strength_model=lora_strength,
            strength_clip=1,
            model=get_value_at_index(loraloader_8, 0),
            clip=get_value_at_index(loraloader_8, 1),
        )

        loraloader_10 = loraloader.load_lora(
            lora_name="more_details.safetensors",
            strength_model=lora_strength * detail_amount,  # Scale by detail amount
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
            unique_id=15560083040652971872,
        )

        # Build dynamic enhancement prompt based on feature parameters
        enhancement_parts = []

        # Base quality
        enhancement_parts.append("photorealistic, masterpiece, intricate details")

        # Object/Product protection
        if protect_objects:
            enhancement_parts.extend(["preserve objects", "maintain product details", "sharp product focus"])
        if protect_hands:
            enhancement_parts.extend(["natural hands", "detailed fingers"])
        if protect_clothing:
            enhancement_parts.extend(["preserve clothing texture", "maintain fabric details"])

        # Face-specific enhancements (only if not in face-only mode or if face_only_mode is True)
        if enhance_skin and (not face_only_mode or face_only_mode):
            skin_terms = ["realistic skin tones", "natural skin texture"]
            if skin_smoothing > 0.5:
                skin_terms.extend(["smooth skin", "flawless complexion"])
            if skin_smoothing > 0.3:
                skin_terms.extend(["visible pores", "skin imperfections"])
            enhancement_parts.extend(skin_terms)

        if enhance_eyes:
            eye_terms = ["detailed eyes", "sharp eyes"]
            if eye_enhancement > 0.7:
                eye_terms.extend(["expressive eyes", "realistic iris", "bright eyes"])
            elif eye_enhancement > 0.5:
                eye_terms.extend(["clear eyes", "focused eyes"])
            enhancement_parts.extend(eye_terms)

        if enhance_hair:
            hair_terms = ["natural hair texture"]
            if hair_detail > 0.7:
                hair_terms.extend(["detailed hair strands", "realistic hair", "flowing hair"])
            elif hair_detail > 0.5:
                hair_terms.extend(["textured hair", "natural hair"])
            enhancement_parts.extend(hair_terms)

        if enhance_lips:
            if lip_enhancement > 0.6:
                enhancement_parts.extend(["natural lips", "detailed lips", "soft lips"])
            elif lip_enhancement > 0.3:
                enhancement_parts.extend(["natural lips", "detailed lips"])

        if enhance_teeth:
            if teeth_whitening > 0.6:
                enhancement_parts.extend(["natural teeth", "white teeth", "clean teeth"])
            elif teeth_whitening > 0.3:
                enhancement_parts.extend(["natural teeth", "white teeth"])

        # Facial area-specific enhancements
        if enhance_cheeks:
            if cheek_enhancement > 0.7:
                enhancement_parts.extend(["defined cheekbones", "natural cheek contour", "smooth cheeks"])
            elif cheek_enhancement > 0.4:
                enhancement_parts.extend(["natural cheeks", "soft cheek definition"])

        if enhance_forehead:
            if forehead_smoothing > 0.6:
                enhancement_parts.extend(["smooth forehead", "even skin tone forehead", "refined forehead"])
            elif forehead_smoothing > 0.3:
                enhancement_parts.extend(["natural forehead", "clear forehead"])

        if enhance_nose:
            if nose_refinement > 0.6:
                enhancement_parts.extend(["refined nose", "natural nose bridge", "detailed nose"])
            elif nose_refinement > 0.3:
                enhancement_parts.extend(["natural nose", "proportioned nose"])

        if enhance_jawline:
            if jawline_definition > 0.6:
                enhancement_parts.extend(["defined jawline", "sharp jawline", "sculpted jaw"])
            elif jawline_definition > 0.3:
                enhancement_parts.extend(["natural jawline", "clean jaw definition"])

        # Lighting and overall enhancements
        lighting_parts = []
        if enhance_lighting:
            lighting_parts.extend(["soft diffused lighting", "natural lighting"])

        if enhance_shadows:
            lighting_parts.append("dynamic shadows")

        if enhance_highlights:
            lighting_parts.append("natural highlights")

        if color_correction > 0.3:
            lighting_parts.append("vibrant colors")

        if contrast_boost > 0.3:
            lighting_parts.append("balanced contrast")

        # Add lighting terms
        if lighting_parts:
            enhancement_parts.extend(lighting_parts)
        else:
            enhancement_parts.append("cinematic lighting")  # Default

        # Technical quality
        enhancement_parts.extend([
            "subsurface scattering", "hyper-detailed shading",
            "8K resolution", "shot on a DSLR with a 50mm lens"
        ])

        # Join enhancement parts
        enhancement_prompt = ", ".join(enhancement_parts)

        print(f"[MAIN] Generated enhancement prompt: {enhancement_prompt}")

        cr_combine_prompt = NODE_CLASS_MAPPINGS["CR Combine Prompt"]()
        cr_combine_prompt_5 = cr_combine_prompt.get_value(
            part1=get_value_at_index(showtextpysssss_4, 0),
            part2=f"and {enhancement_prompt}.",
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
            text="(3d, render, cgi, doll, painting, fake, cartoon, 3d modeling:1.4), (worst quality, low quality:1.4), monochrome, deformed, malformed, deformed face, bad teeth, bad hands, bad fingers, bad eyes, long body, blurry, duplicate, cloned, duplicate body parts, disfigured, extra limbs, fused fingers, extra fingers, twisted, distorted, malformed hands, mutated hands and fingers, conjoined, missing limbs, bad anatomy, bad proportions, logo, watermark, text, copyright, signature, lowres, mutated, mutilated, artifacts, gross, ugly, (adult:1.5), (mature features:1.5)",
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

        checkpointloadersimple_184 = checkpointloadersimple.load_checkpoint(
            ckpt_name="STOIQOAfroditexl_XL31.safetensors"
        )

        cliptextencode_179 = cliptextencode.encode(
            text=get_value_at_index(cr_combine_prompt_5, 0),
            clip=get_value_at_index(checkpointloadersimple_184, 1),
        )

        cliptextencode_180 = cliptextencode.encode(
            text="(3d, render, cgi, doll, painting, fake, cartoon, 3d modeling:1.4), (worst quality, low quality:1.4), monochrome, deformed, malformed, deformed face, bad teeth, bad hands, bad fingers, bad eyes, long body, blurry, duplicate, cloned, duplicate body parts, disfigured, extra limbs, fused fingers, extra fingers, twisted, distorted, malformed hands, mutated hands and fingers, conjoined, missing limbs, bad anatomy, bad proportions, logo, watermark, text, copyright, signature, lowres, mutated, mutilated, artifacts, gross, ugly, (adult:1.5), (mature features:1.5)",
            clip=get_value_at_index(checkpointloadersimple_184, 1),
        )

        ksamplerselect = NODE_CLASS_MAPPINGS["KSamplerSelect"]()
        ksamplerselect_182 = ksamplerselect.get_sampler(sampler_name="dpmpp_2m_sde")

        upscalemodelloader = NODE_CLASS_MAPPINGS["UpscaleModelLoader"]()
        upscalemodelloader_183 = upscalemodelloader.load_model(
            model_name="4x_NMKD-Siax_200k.pth"
        )

        upscalemodelloader_188 = upscalemodelloader.load_model(
            model_name="4x_NMKD-Siax_200k.pth"
        )

        ksamplerselect_208 = ksamplerselect.get_sampler(sampler_name="dpmpp_2m_sde")

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
        get_image_size = NODE_CLASS_MAPPINGS["Get Image Size"]()
        detaildaemonsamplernode = NODE_CLASS_MAPPINGS["DetailDaemonSamplerNode"]()
        ultimatesdupscalecustomsample = NODE_CLASS_MAPPINGS[
            "UltimateSDUpscaleCustomSample"
        ]()
        imageresizekjv2 = NODE_CLASS_MAPPINGS["ImageResizeKJv2"]()
        cr_simple_image_compare = NODE_CLASS_MAPPINGS["CR Simple Image Compare"]()
        imageupscalewithmodel = NODE_CLASS_MAPPINGS["ImageUpscaleWithModel"]()
        imagescaleby = NODE_CLASS_MAPPINGS["ImageScaleBy"]()
        getimagesize = NODE_CLASS_MAPPINGS["GetImageSize+"]()
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
                    background=False,
                    skin=False,
                    nose=False,
                    eye_g=True,
                    r_eye=True,
                    l_eye=True,
                    r_brow=False,
                    l_brow=False,
                    r_ear=False,
                    l_ear=False,
                    mouth=False,
                    u_lip=True,
                    l_lip=True,
                    hair=False,
                    hat=False,
                    ear_r=False,
                    neck_l=False,
                    neck=False,
                    cloth=True,
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
                steps=steps,
                cfg=cfg_scale,
                sampler_name="dpmpp_2m_sde",
                scheduler="karras",
                denoise=denoise_strength,
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
                guidance=3, conditioning=get_value_at_index(cliptextencode_30, 0)
            )

            # Adjust FaceDetailer parameters based on facial enhancement settings
            # Calculate enhancement intensity based on all facial area parameters
            facial_enhancement_intensity = max(
                eye_enhancement if enhance_eyes else 0,
                skin_smoothing if enhance_skin else 0,
                cheek_enhancement if enhance_cheeks else 0,
                forehead_smoothing if enhance_forehead else 0,
                nose_refinement if enhance_nose else 0,
                jawline_definition if enhance_jawline else 0
            )

            # Dynamic parameters based on highest enhancement level
            if facial_enhancement_intensity > 0.7:
                face_steps = int(steps * 0.8)  # High detail processing
                face_denoise = min(0.4, denoise_strength * 2.5)
                face_cfg = min(4, cfg_scale)
                bbox_crop_factor = 3.5  # Larger crop for detailed work
            elif facial_enhancement_intensity > 0.5:
                face_steps = int(steps * 0.6)  # Medium detail processing
                face_denoise = min(0.3, denoise_strength * 2)
                face_cfg = min(3, cfg_scale)
                bbox_crop_factor = 3.0  # Standard crop
            elif facial_enhancement_intensity > 0.3:
                face_steps = int(steps * 0.4)  # Light processing
                face_denoise = min(0.2, denoise_strength * 1.5)
                face_cfg = min(2, cfg_scale)
                bbox_crop_factor = 2.5  # Smaller crop for light work
            else:
                face_steps = 15  # Minimal processing
                face_denoise = 0.12
                face_cfg = 1
                bbox_crop_factor = 2.0

            print(f"[MAIN] Facial enhancement intensity: {facial_enhancement_intensity:.2f}")
            print(f"[MAIN] FaceDetailer settings - Steps: {face_steps}, CFG: {face_cfg}, Denoise: {face_denoise:.3f}, Crop: {bbox_crop_factor}")

            facedetailer_29 = facedetailer.doit(
                guide_size=512,
                guide_size_for=True,
                max_size=1024,
                seed=random.randint(1, 2**64),
                steps=face_steps,  # Dynamic steps based on face enhancement
                cfg=face_cfg,  # Dynamic CFG based on face enhancement
                sampler_name="euler",
                scheduler="normal",
                denoise=face_denoise,  # Dynamic denoise based on skin enhancement
                feather=5,
                noise_mask=True,
                force_inpaint=True,
                bbox_threshold=0.5,
                bbox_dilation=10,
                bbox_crop_factor=bbox_crop_factor,  # Dynamic crop based on enhancement intensity
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

            get_image_size_186 = get_image_size.get_size(
                image=get_value_at_index(loadimage_1, 0)
            )

            # Adjust DetailDaemon based on facial area enhancement settings
            # Higher detail for specific facial areas
            facial_detail_boost = 1.0
            if enhance_cheeks and cheek_enhancement > 0.6:
                facial_detail_boost += 0.2
            if enhance_forehead and forehead_smoothing > 0.6:
                facial_detail_boost += 0.15
            if enhance_nose and nose_refinement > 0.6:
                facial_detail_boost += 0.1
            if enhance_jawline and jawline_definition > 0.6:
                facial_detail_boost += 0.15

            enhanced_detail_amount = min(1.0, detail_amount * facial_detail_boost)
            print(f"[MAIN] DetailDaemon - Base detail: {detail_amount:.2f}, Facial boost: {facial_detail_boost:.2f}, Final: {enhanced_detail_amount:.2f}")

            detaildaemonsamplernode_181 = detaildaemonsamplernode.go(
                detail_amount=enhanced_detail_amount,  # Enhanced detail based on facial areas
                start=0.5000000000000001,
                end=0.7000000000000002,
                bias=0.6000000000000001,
                exponent=0,
                start_offset=0,
                end_offset=0,
                fade=0,
                smooth=True,
                cfg_scale_override=cfg_scale,
                sampler=get_value_at_index(ksamplerselect_182, 0),
            )

            ultimatesdupscalecustomsample_178 = ultimatesdupscalecustomsample.upscale(
                upscale_by=upscale_factor,
                seed=random.randint(1, 2**64),
                steps=int(steps * 0.75),  # Use 75% of steps for upscaling
                cfg=max(3, int(cfg_scale * 0.5)),  # Lower CFG for upscaling
                sampler_name="dpmpp_2m_sde",
                scheduler="karras",
                denoise=denoise_strength * 0.5,  # Lower denoise for upscaling
                mode_type="Linear",
                tile_width=1024,
                tile_height=1024,
                mask_blur=8,
                tile_padding=32,
                seam_fix_mode="None",
                seam_fix_denoise=1,
                seam_fix_width=64,
                seam_fix_mask_blur=8,
                seam_fix_padding=16,
                force_uniform_tiles=True,
                tiled_decode=False,
                image=get_value_at_index(facedetailer_29, 0),
                model=get_value_at_index(checkpointloadersimple_184, 0),
                positive=get_value_at_index(cliptextencode_179, 0),
                negative=get_value_at_index(cliptextencode_180, 0),
                vae=get_value_at_index(checkpointloadersimple_184, 2),
                upscale_model=get_value_at_index(upscalemodelloader_183, 0),
                custom_sampler=get_value_at_index(detaildaemonsamplernode_181, 0),
            )

            # REMOVED SECOND UPSCALER FOR FASTER PROCESSING
            # Using only the first upscaler (ultimatesdupscalecustomsample_178) as final output
            print(f"[MAIN] Skipping second upscaler for faster processing")

            imageresizekjv2_185 = imageresizekjv2.resize(
                width=get_value_at_index(get_image_size_186, 0),
                height=get_value_at_index(get_image_size_186, 1),
                upscale_method="nearest-exact",
                keep_proportion="resize",
                pad_color="0, 0, 0",
                crop_position="center",
                divisible_by=2,
                device="gpu",
                image=get_value_at_index(ultimatesdupscalecustomsample_178, 0),  # Use first upscaler output
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
                image2=get_value_at_index(imageresizekjv2_185, 0),
            )

            image_comparer_rgthree_176 = image_comparer_rgthree.compare_images(
                image_a=get_value_at_index(loadimage_1, 0),
                image_b=get_value_at_index(ultimatesdupscalecustomsample_178, 0),
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

            image_comparer_rgthree_195 = image_comparer_rgthree.compare_images(
                image_a=get_value_at_index(loadimage_1, 0),
                image_b=get_value_at_index(ultimatesdupscalecustomsample_178, 0),  # Use first upscaler output
            )

            saveimage_202 = saveimage.save_images(
                filename_prefix="RealSkin AI Lite Comparer Original Vs Final",
                images=get_value_at_index(cr_simple_image_compare_74, 0),
            )

            saveimage_203 = saveimage.save_images(
                filename_prefix="RealSkin AI Light Final Resized to Original Scale",
                images=get_value_at_index(imageresizekjv2_185, 0),
            )

            saveimage_204 = saveimage.save_images(
                filename_prefix="RealSkin AI Light Final Hi-Rez Output",
                images=get_value_at_index(ultimatesdupscalecustomsample_178, 0),  # Use first upscaler output
            )

            saveimage_205 = saveimage.save_images(
                filename_prefix="RealSkin AI Light First Hi-Rez Output",
                images=get_value_at_index(ultimatesdupscalecustomsample_178, 0),
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

    # Final cleanup in main function
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

    # Clean up GPU memory immediately after ComfyUI processing
    print("[MAIN] Cleaning up GPU memory after ComfyUI processing")
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            print("[MAIN] ✅ GPU memory cache cleared")
        gc.collect()
        print("[MAIN] ✅ Python garbage collection completed")
    except Exception as e:
        print(f"[MAIN] GPU cleanup warning: {e}")


def runpod_handler(job):
    """
    RunPod serverless handler function.

    Expected input format:
    {
        "input": {
            "image_id": "image_filename.jpg"  # Optional, defaults to "Asian+Man+1+Before.jpg"
        }
    }

    Returns:
    {
        "status": "success" | "error",
        "message": "Success/error message",
        "outputs": {
            "comparison_image": "path_to_comparison_image",
            "final_resized": "path_to_final_resized_image",
            "final_hires": "path_to_final_hires_image",
            "first_hires": "path_to_first_hires_image"
        }
    }
    """
    import traceback
    import logging
    import os
    import sys
    import glob
    import time
    import gc

    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Log runtime environment verification
        logger.info("=== RUNPOD HANDLER EXECUTION START ===")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Python path: {sys.path}")
        logger.info(f"Handler file location: {__file__}")

        # Verify critical paths exist
        comfyui_path = "/runpod-volume/ComfyUI"
        logger.info(f"ComfyUI path exists: {os.path.exists(comfyui_path)}")
        if os.path.exists(comfyui_path):
            logger.info(f"ComfyUI contents: {os.listdir(comfyui_path)[:10]}...")  # First 10 items

        models_path = "/runpod-volume/ComfyUI/models"
        logger.info(f"Models path exists: {os.path.exists(models_path)}")
        if os.path.exists(models_path):
            logger.info(f"Models subdirs: {os.listdir(models_path)}")

        output_path = "/runpod-volume/ComfyUI/output"
        logger.info(f"Output path exists: {os.path.exists(output_path)}")

        # Extract input parameters
        input_data = job.get("input", {})
        image_id = input_data.get("image_id", "Asian+Man+1+Before.jpg")
        detail_amount = float(input_data.get("detail_amount", 0.7))
        denoise_strength = float(input_data.get("denoise_strength", 0.3))
        cfg_scale = int(input_data.get("cfg_scale", 6))
        upscale_factor = float(input_data.get("upscale_factor", 2.0))
        steps = int(input_data.get("steps", 40))
        lora_strength = float(input_data.get("lora_strength", 1.2))

        # Face Enhancement Parameters
        enhance_eyes = input_data.get("enhance_eyes", True)
        enhance_skin = input_data.get("enhance_skin", True)
        enhance_hair = input_data.get("enhance_hair", True)
        enhance_lips = input_data.get("enhance_lips", True)
        enhance_teeth = input_data.get("enhance_teeth", True)

        # Facial Area Enhancement Parameters
        enhance_cheeks = input_data.get("enhance_cheeks", True)
        enhance_forehead = input_data.get("enhance_forehead", True)
        enhance_nose = input_data.get("enhance_nose", True)
        enhance_jawline = input_data.get("enhance_jawline", True)

        # Feature Strength Parameters
        eye_enhancement = float(input_data.get("eye_enhancement", 0.8))
        skin_smoothing = float(input_data.get("skin_smoothing", 0.6))
        hair_detail = float(input_data.get("hair_detail", 0.7))
        lip_enhancement = float(input_data.get("lip_enhancement", 0.5))
        teeth_whitening = float(input_data.get("teeth_whitening", 0.4))

        # Facial Area Strength Parameters
        cheek_enhancement = float(input_data.get("cheek_enhancement", 0.6))
        forehead_smoothing = float(input_data.get("forehead_smoothing", 0.5))
        nose_refinement = float(input_data.get("nose_refinement", 0.4))
        jawline_definition = float(input_data.get("jawline_definition", 0.5))

        # Overall Enhancement Parameters
        enhance_lighting = input_data.get("enhance_lighting", True)
        enhance_shadows = input_data.get("enhance_shadows", True)
        enhance_highlights = input_data.get("enhance_highlights", True)
        color_correction = float(input_data.get("color_correction", 0.5))
        contrast_boost = float(input_data.get("contrast_boost", 0.3))

        # Object/Product Protection Parameters
        protect_objects = input_data.get("protect_objects", True)
        protect_hands = input_data.get("protect_hands", True)
        protect_clothing = input_data.get("protect_clothing", True)
        face_only_mode = input_data.get("face_only_mode", False)

        logger.info(f"Processing image: {image_id}")
        logger.info(f"Enhancement parameters:")
        logger.info(f"  - Detail Amount: {detail_amount}")
        logger.info(f"  - Denoise Strength: {denoise_strength}")
        logger.info(f"  - CFG Scale: {cfg_scale}")
        logger.info(f"  - Upscale Factor: {upscale_factor}")
        logger.info(f"  - Steps: {steps}")
        logger.info(f"  - LoRA Strength: {lora_strength}")
        logger.info("=== STARTING MAIN PROCESSING ===")

        # Pre-processing GPU memory cleanup to ensure clean start
        logger.info("=== PRE-PROCESSING GPU CLEANUP ===")
        try:
            if torch.cuda.is_available():
                memory_before = torch.cuda.memory_allocated() / 1024**3
                logger.info(f"GPU Memory before pre-cleanup: {memory_before:.2f}GB")

                # Clear any leftover memory from previous jobs
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                gc.collect()

                memory_after = torch.cuda.memory_allocated() / 1024**3
                logger.info(f"GPU Memory after pre-cleanup: {memory_after:.2f}GB")
                logger.info(f"Pre-cleanup freed: {memory_before - memory_after:.2f}GB")
        except Exception as pre_cleanup_error:
            logger.warning(f"Pre-cleanup warning: {pre_cleanup_error}")

        # Run the main processing function
        logger.info("=== STARTING MAIN PROCESSING FUNCTION ===")
        main(
            image_id=image_id,
            detail_amount=detail_amount,
            denoise_strength=denoise_strength,
            cfg_scale=cfg_scale,
            upscale_factor=upscale_factor,
            steps=steps,
            lora_strength=lora_strength,
            # Face Enhancement Parameters
            enhance_eyes=enhance_eyes,
            enhance_skin=enhance_skin,
            enhance_hair=enhance_hair,
            enhance_lips=enhance_lips,
            enhance_teeth=enhance_teeth,
            # Facial Area Enhancement Parameters
            enhance_cheeks=enhance_cheeks,
            enhance_forehead=enhance_forehead,
            enhance_nose=enhance_nose,
            enhance_jawline=enhance_jawline,
            # Feature Strength Parameters
            eye_enhancement=eye_enhancement,
            skin_smoothing=skin_smoothing,
            hair_detail=hair_detail,
            lip_enhancement=lip_enhancement,
            teeth_whitening=teeth_whitening,
            # Facial Area Strength Parameters
            cheek_enhancement=cheek_enhancement,
            forehead_smoothing=forehead_smoothing,
            nose_refinement=nose_refinement,
            jawline_definition=jawline_definition,
            # Overall Enhancement Parameters
            enhance_lighting=enhance_lighting,
            enhance_shadows=enhance_shadows,
            enhance_highlights=enhance_highlights,
            color_correction=color_correction,
            contrast_boost=contrast_boost,
            # Object/Product Protection Parameters
            protect_objects=protect_objects,
            protect_hands=protect_hands,
            protect_clothing=protect_clothing,
            face_only_mode=face_only_mode
        )
        logger.info("=== MAIN PROCESSING FUNCTION COMPLETED ===")

        # The main function saves images to ComfyUI's output directory
        # We need to return the paths to the generated images
        output_dir = "/runpod-volume/ComfyUI/output"
        logger.info(f"Looking for output files in: {output_dir}")

        # Check if output directory exists and list its contents
        if os.path.exists(output_dir):
            all_files = os.listdir(output_dir)
            logger.info(f"Output directory contains {len(all_files)} files:")
            for file in sorted(all_files):
                file_path = os.path.join(output_dir, file)
                file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
                logger.info(f"  - {file} ({file_size} bytes)")
        else:
            logger.error(f"Output directory does not exist: {output_dir}")

        # Find the most recent output files
        logger.info("=== SEARCHING FOR OUTPUT FILES ===")
        # Get the most recent files for each type
        comparison_files = glob.glob(os.path.join(output_dir, "*Comparer Original Vs Final*"))
        final_resized_files = glob.glob(os.path.join(output_dir, "*Final Resized to Original Scale*"))
        final_hires_files = glob.glob(os.path.join(output_dir, "*Final Hi-Rez Output*"))
        first_hires_files = glob.glob(os.path.join(output_dir, "*First Hi-Rez Output*"))

        logger.info(f"Found comparison files: {comparison_files}")
        logger.info(f"Found final_resized files: {final_resized_files}")
        logger.info(f"Found final_hires files: {final_hires_files}")
        logger.info(f"Found first_hires files: {first_hires_files}")

        # Sort by modification time and get the most recent
        def get_latest_file(file_list):
            if not file_list:
                return None
            return max(file_list, key=os.path.getmtime)

        outputs = {
            "comparison_image": get_latest_file(comparison_files),
            "final_resized": get_latest_file(final_resized_files),
            "final_hires": get_latest_file(final_hires_files),
            "first_hires": get_latest_file(first_hires_files)
        }

        # Filter out None values
        outputs = {k: v for k, v in outputs.items() if v is not None}

        logger.info(f"Generated outputs: {list(outputs.keys())}")
        logger.info("=== OUTPUT FILES SUMMARY ===")
        for key, file_path in outputs.items():
            if file_path:
                exists = os.path.exists(file_path)
                size = os.path.getsize(file_path) if exists else 0
                logger.info(f"  {key}: {file_path} (exists: {exists}, size: {size} bytes)")
            else:
                logger.info(f"  {key}: None")

        # Upload outputs to B2 storage
        from b2_config import upload_file_to_b2
        uploaded_outputs = {}

        logger.info("=== STARTING B2 UPLOAD PROCESS ===")
        if not outputs:
            logger.warning("No output files to upload to B2")
        else:
            logger.info(f"Uploading {len(outputs)} files to B2...")

        for key, file_path in outputs.items():
            logger.info(f"Processing {key}: {file_path}")
            if file_path and os.path.exists(file_path):
                try:
                    # Generate a unique filename for B2
                    filename = os.path.basename(file_path)
                    timestamp = int(time.time())
                    b2_filename = f"realism_output_{timestamp}_{filename}"

                    logger.info(f"Uploading {file_path} as {b2_filename}...")
                    # Upload to B2
                    b2_url = upload_file_to_b2(file_path, b2_filename)
                    uploaded_outputs[key] = {
                        "local_path": file_path,
                        "b2_url": b2_url,
                        "b2_filename": b2_filename
                    }
                    logger.info(f"✅ Successfully uploaded {key}: {b2_filename} -> {b2_url}")
                except Exception as e:
                    logger.error(f"❌ Failed to upload {key}: {e}")
                    logger.error(f"   File path: {file_path}")
                    logger.error(f"   File exists: {os.path.exists(file_path)}")
                    uploaded_outputs[key] = {
                        "local_path": file_path,
                        "error": str(e)
                    }
            else:
                logger.warning(f"⚠️ File not found for {key}: {file_path}")
                logger.warning(f"   File exists check: {os.path.exists(file_path) if file_path else 'N/A'}")

        logger.info(f"=== B2 UPLOAD COMPLETE: {len(uploaded_outputs)} files processed ===")

        # Aggressive GPU memory cleanup after processing
        logger.info("=== AGGRESSIVE GPU MEMORY CLEANUP ===")
        try:
            if torch.cuda.is_available():
                # Log memory before cleanup
                memory_before = torch.cuda.memory_allocated() / 1024**3
                reserved_before = torch.cuda.memory_reserved() / 1024**3
                logger.info(f"GPU Memory BEFORE cleanup - Allocated: {memory_before:.2f}GB, Reserved: {reserved_before:.2f}GB")

                # Multiple cleanup passes
                for i in range(3):
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    gc.collect()
                    logger.info(f"✅ GPU cleanup pass {i+1}/3 completed")

                # Force reset of memory stats
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.reset_accumulated_memory_stats()

                # Final memory check
                memory_after = torch.cuda.memory_allocated() / 1024**3
                reserved_after = torch.cuda.memory_reserved() / 1024**3
                logger.info(f"GPU Memory AFTER cleanup - Allocated: {memory_after:.2f}GB, Reserved: {reserved_after:.2f}GB")
                logger.info(f"Memory freed: {memory_before - memory_after:.2f}GB")

            # Multiple garbage collection passes
            for i in range(3):
                collected = gc.collect()
                logger.info(f"✅ Python garbage collection pass {i+1}/3: {collected} objects collected")

        except Exception as cleanup_error:
            logger.warning(f"GPU cleanup warning: {cleanup_error}")

        return {
            "status": "success",
            "message": f"Successfully processed image: {image_id}",
            "outputs": outputs,
            "b2_uploads": uploaded_outputs
        }

    except Exception as e:
        error_msg = f"Error processing image: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())

        # Aggressive GPU memory cleanup even on error
        logger.info("=== AGGRESSIVE GPU MEMORY CLEANUP (ERROR CASE) ===")
        try:
            if torch.cuda.is_available():
                # Log memory before cleanup
                memory_before = torch.cuda.memory_allocated() / 1024**3
                logger.info(f"GPU Memory before error cleanup: {memory_before:.2f}GB")

                # Multiple aggressive cleanup passes
                for i in range(5):  # More passes on error
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    gc.collect()
                    logger.info(f"✅ Error cleanup pass {i+1}/5 completed")

                # Force reset everything
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.reset_accumulated_memory_stats()

                memory_after = torch.cuda.memory_allocated() / 1024**3
                logger.info(f"GPU Memory after error cleanup: {memory_after:.2f}GB")
                logger.info(f"Memory freed on error: {memory_before - memory_after:.2f}GB")

            # Multiple garbage collection passes
            for i in range(5):
                collected = gc.collect()
                logger.info(f"✅ Error garbage collection pass {i+1}/5: {collected} objects collected")

        except Exception as cleanup_error:
            logger.warning(f"GPU cleanup warning after error: {cleanup_error}")

        return {
            "status": "error",
            "message": error_msg,
            "traceback": traceback.format_exc()
        }


if __name__ == "__main__":
    # Parse command line arguments and pass image_id to main
    args = parse_arguments()
    main(image_id=args.image_id)
