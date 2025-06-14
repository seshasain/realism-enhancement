import os
import random
import sys
import json
import argparse
from typing import Sequence, Mapping, Any, Union, Dict
import torch
import tempfile
from b2_config import download_file_from_b2, upload_file_to_b2


# Define paths for RunPod environments
RUNPOD_VOLUME = "/runpod-volume"  # Always use the network volume
COMFYUI_PATH = os.path.join(RUNPOD_VOLUME, "ComfyUI")
TEMP_DIR = os.path.join(RUNPOD_VOLUME, "tmp")
OUTPUT_DIR = os.path.join(RUNPOD_VOLUME, "outputs")

# Create necessary directories
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Ensure ComfyUI path exists
if not os.path.exists(COMFYUI_PATH):
    raise RuntimeError(f"ComfyUI not found in network volume: {COMFYUI_PATH}")


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
        print(
            "Could not import load_extra_path_config from main.py. Looking in utils.extra_config instead."
        )
        from utils.extra_config import load_extra_path_config

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


from nodes import NODE_CLASS_MAPPINGS


def setup_runpod_environment() -> None:
    """
    Setup the environment for RunPod execution.
    Uses network storage at /runpod-volume.
    """
    # Add ComfyUI to sys.path
    if os.path.isdir(COMFYUI_PATH):
        sys.path.append(COMFYUI_PATH)
        print(f"Added ComfyUI path: {COMFYUI_PATH}")
    else:
        raise RuntimeError(f"ComfyUI not found in network volume: {COMFYUI_PATH}")

    # Change working directory to ComfyUI
    os.chdir(COMFYUI_PATH)
    print(f"Changed working directory to: {os.getcwd()}")

    # Load extra model paths if config exists
    extra_model_paths = os.path.join(COMFYUI_PATH, "extra_model_paths.yaml")
    if os.path.exists(extra_model_paths):
        try:
            from main import load_extra_path_config
        except ImportError:
            from utils.extra_config import load_extra_path_config
        load_extra_path_config(extra_model_paths)
        print("Loaded extra model paths configuration")


def load_image_from_b2(image_id: str) -> str:
    """Downloads an image from B2 and returns the local path.
    
    Args:
        image_id (str): The image ID/name in the B2 bucket
        
    Returns:
        str: Local path to the downloaded image
    """
    # Create a directory to store the downloaded image in network storage
    temp_dir = os.path.join(TEMP_DIR, "b2_images")
    os.makedirs(temp_dir, exist_ok=True)
    
    local_path = os.path.join(temp_dir, image_id)
    
    # Download the image from B2
    print(f"Downloading image {image_id} from B2 storage...")
    download_file_from_b2(image_id, local_path)
    print(f"Image downloaded to {local_path}")
    
    return local_path


def save_outputs_to_b2(output_files: Dict[str, str]) -> Dict[str, str]:
    """
    Uploads output files to B2 storage and returns their URLs.
    Also saves copies to the network volume.
    
    Args:
        output_files: Dictionary mapping output names to local file paths
        
    Returns:
        Dictionary mapping output names to B2 URLs
    """
    result = {}
    for name, path in output_files.items():
        if os.path.exists(path):
            # Use the filename as the object name in B2
            object_name = os.path.basename(path)
            
            # Upload to B2
            url = upload_file_to_b2(path, object_name)
            result[name] = url
            print(f"Uploaded {name} to {url}")
            
            # Also save to network volume
            persistent_path = os.path.join(OUTPUT_DIR, object_name)
            try:
                import shutil
                shutil.copy2(path, persistent_path)
                print(f"Saved output to network volume: {persistent_path}")
            except Exception as e:
                print(f"Failed to save to network volume: {e}")
        else:
            print(f"Warning: Output file {path} does not exist")
    
    return result


def runpod_handler(event):
    """
    Handler function for RunPod serverless execution.
    
    Args:
        event: RunPod event object with input parameters
        
    Returns:
        Dictionary with output URLs
    """
    try:
        # Get parameters from the event input
        input_data = event.get("input", {})
        image_id = input_data.get("image_id", "Asian+Man+1+Before.jpg")
        
        # Extract realism parameters with defaults
        params = {
            "detail_amount": input_data.get("detail_amount", 0.7),
            "denoise_strength": input_data.get("denoise_strength", 0.3),
            "cfg_scale": input_data.get("cfg_scale", 6),
            "upscale_factor": input_data.get("upscale_factor", 2.0),
            "skin_retouching": input_data.get("skin_retouching", 0.2),
            "seed": input_data.get("seed", None)  # Random seed if None
        }
        
        # Process the image
        output_files = main(image_id, **params)
        
        # Upload results to B2
        output_urls = save_outputs_to_b2(output_files)
        
        # Return the output URLs
        return {
            "output": output_urls
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def main(
    image_id: str = "Asian+Man+1+Before.jpg",
    detail_amount: float = 0.7,
    denoise_strength: float = 0.3,
    cfg_scale: float = 6,
    upscale_factor: float = 2.0,
    skin_retouching: float = 0.2,
    seed: int = None
) -> Dict[str, str]:
    """
    Main function to process an image using ComfyUI nodes.
    
    Args:
        image_id (str): ID of the image in B2 storage to process
        detail_amount (float): Amount of detail to add (0.0-1.0)
        denoise_strength (float): Strength of the denoising (0.0-1.0)
        cfg_scale (float): CFG scale for stable diffusion (1.0-20.0)
        upscale_factor (float): Factor to upscale the image by (1.0-4.0)
        skin_retouching (float): Amount of skin retouching (0.0-1.0)
        seed (int): Random seed for reproducibility (None for random)
        
    Returns:
        Dictionary mapping output names to local file paths
    """
    # Setup RunPod environment
    setup_runpod_environment()
    
    # Import custom nodes
    import_custom_nodes()
    
    # Download image from B2 storage
    image_path = load_image_from_b2(image_id)
    
    # Dictionary to store output file paths
    output_files = {}
    
    # Use provided seed or generate random one
    if seed is None:
        seed = random.randint(1, 2**64)
    
    print(f"Processing with parameters: detail_amount={detail_amount}, denoise_strength={denoise_strength}, "
          f"cfg_scale={cfg_scale}, upscale_factor={upscale_factor}, skin_retouching={skin_retouching}, seed={seed}")
    
    with torch.inference_mode():
        loadimage = NODE_CLASS_MAPPINGS["LoadImage"]()
        loadimage_1 = loadimage.load_image(image=image_path)

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
            unique_id=15560083040652971872,
        )

        cr_combine_prompt = NODE_CLASS_MAPPINGS["CR Combine Prompt"]()
        cr_combine_prompt_5 = cr_combine_prompt.get_value(
            part1=get_value_at_index(showtextpysssss_4, 0),
            part2="and realistic skin tones, imperfections and visible pores, photorealistic, soft diffused lighting, subsurface scattering, hyper-detailed shading, dynamic shadows, 8K resolution, cinematic lighting, masterpiece, intricate details, shot on a DSLR with a 50mm lens.",
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
                seed=seed,  # Use provided or generated seed
                steps=40,
                cfg=cfg_scale,  # Use provided cfg_scale
                sampler_name="dpmpp_2m_sde",
                scheduler="karras",
                denoise=denoise_strength,  # Use provided denoise_strength
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

            facedetailer_29 = facedetailer.doit(
                guide_size=512,
                guide_size_for=True,
                max_size=1024,
                seed=random.randint(1, 2**64),
                steps=20,
                cfg=1,
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

            get_image_size_186 = get_image_size.get_size(
                image=get_value_at_index(loadimage_1, 0)
            )

            detaildaemonsamplernode_181 = detaildaemonsamplernode.go(
                detail_amount=detail_amount,  # Use provided detail_amount
                start=0.5000000000000001,
                end=0.7000000000000002,
                bias=0.6000000000000001,
                exponent=0,
                start_offset=0,
                end_offset=0,
                fade=0,
                smooth=True,
                cfg_scale_override=0,
                sampler=get_value_at_index(ksamplerselect_182, 0),
            )

            ultimatesdupscalecustomsample_178 = ultimatesdupscalecustomsample.upscale(
                upscale_by=upscale_factor,  # Use provided upscale_factor
                seed=seed,  # Use provided or generated seed
                steps=30,
                cfg=3,
                sampler_name="dpmpp_2m_sde",
                scheduler="karras",
                denoise=0.15000000000000002,
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

            detaildaemonsamplernode_207 = detaildaemonsamplernode.go(
                detail_amount=skin_retouching,  # Use provided skin_retouching parameter
                start=0.5000000000000001,
                end=0.7000000000000002,
                bias=0.6000000000000001,
                exponent=0,
                start_offset=0,
                end_offset=0,
                fade=0,
                smooth=True,
                cfg_scale_override=0,
                sampler=get_value_at_index(ksamplerselect_208, 0),
            )

            ultimatesdupscalecustomsample_194 = ultimatesdupscalecustomsample.upscale(
                upscale_by=2.0000000000000004,
                seed=random.randint(1, 2**64),
                steps=30,
                cfg=3,
                sampler_name="dpmpp_2m_sde",
                scheduler="karras",
                denoise=0.15000000000000002,
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
                image=get_value_at_index(ultimatesdupscalecustomsample_178, 0),
                model=get_value_at_index(checkpointloadersimple_184, 0),
                positive=get_value_at_index(cliptextencode_179, 0),
                negative=get_value_at_index(cliptextencode_180, 0),
                vae=get_value_at_index(checkpointloadersimple_184, 2),
                upscale_model=get_value_at_index(upscalemodelloader_183, 0),
                custom_sampler=get_value_at_index(detaildaemonsamplernode_207, 0),
            )

            imageresizekjv2_185 = imageresizekjv2.resize(
                width=get_value_at_index(get_image_size_186, 0),
                height=get_value_at_index(get_image_size_186, 1),
                upscale_method="nearest-exact",
                keep_proportion="resize",
                pad_color="0, 0, 0",
                crop_position="center",
                divisible_by=2,
                device="gpu",
                image=get_value_at_index(ultimatesdupscalecustomsample_194, 0),
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
                image_b=get_value_at_index(ultimatesdupscalecustomsample_194, 0),
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
                images=get_value_at_index(ultimatesdupscalecustomsample_194, 0),
            )

            saveimage_205 = saveimage.save_images(
                filename_prefix="RealSkin AI Light First Hi-Rez Output",
                images=get_value_at_index(ultimatesdupscalecustomsample_178, 0),
            )

        # At the end of the processing, store the output file paths
        output_files["comparison"] = saveimage_202["ui"]["images"][0]["filename"]
        output_files["final_resized"] = saveimage_203["ui"]["images"][0]["filename"]
        output_files["final_hi_rez"] = saveimage_204["ui"]["images"][0]["filename"]
        output_files["first_hi_rez"] = saveimage_205["ui"]["images"][0]["filename"]
        
        return output_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process an image using ComfyUI nodes")
    parser.add_argument("--image_id", type=str, default="Asian+Man+1+Before.jpg",
                        help="ID of the image in B2 storage to process")
    parser.add_argument("--detail_amount", type=float, default=0.7,
                        help="Amount of detail to add (0.0-1.0)")
    parser.add_argument("--denoise_strength", type=float, default=0.3,
                        help="Strength of the denoising (0.0-1.0)")
    parser.add_argument("--cfg_scale", type=float, default=6.0,
                        help="CFG scale for stable diffusion (1.0-20.0)")
    parser.add_argument("--upscale_factor", type=float, default=2.0,
                        help="Factor to upscale the image by (1.0-4.0)")
    parser.add_argument("--skin_retouching", type=float, default=0.2,
                        help="Amount of skin retouching (0.0-1.0)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--runpod", action="store_true",
                        help="Run in RunPod serverless mode (read input from environment)")
    
    args = parser.parse_args()
    
    if args.runpod:
        # RunPod serverless mode - get input from environment
        if "RUNPOD_INPUT" in os.environ:
            event = json.loads(os.environ["RUNPOD_INPUT"])
            result = runpod_handler(event)
            # Print result for RunPod to capture
            print(json.dumps(result))
        else:
            print("Error: RUNPOD_INPUT environment variable not found")
            sys.exit(1)
    else:
        # Normal mode - process image directly
        result = main(
            image_id=args.image_id,
            detail_amount=args.detail_amount,
            denoise_strength=args.denoise_strength,
            cfg_scale=args.cfg_scale,
            upscale_factor=args.upscale_factor,
            skin_retouching=args.skin_retouching,
            seed=args.seed
        )
        print("Processing complete. Output files:")
        for name, path in result.items():
            print(f"  {name}: {path}")
