import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from PIL import Image
import json
import argparse
import image_processing_utils

# Collect arguments from cmd line and parse them
from classifier_network import construct_model

ap = argparse.ArgumentParser(description="This file loads a pretrained model checkpoint and predict a flower name "
                                         "from the image and displays the probabilities",
                             formatter_class=argparse.ArgumentDefaultsHelpFormatter)
ap.add_argument("image_path", metavar="image_path", help="Location where test image is stored", type=str)
ap.add_argument("checkpoint_file", metavar="checkpoint_file", help="filename of the saved model checkpoint", type=str)
ap.add_argument("--top_k", help="Returns top most likely classes", default="5", type=int)
ap.add_argument("--category_names_file", help="file for mapping of categories to names", default="", type=str)
ap.add_argument("--gpu", help="Use gpu for inference", default="cpu", type=str)
args = vars(ap.parse_args())

print("image_path : ", args["image_path"])

# Initialization
checkpoint_file = args["checkpoint_file"]  # 'trained_model_chpt.pth'
top_k = args["top_k"]
category_names_file = args["category_names_file"]  # 'cat_to_name.json'
image_path = args["image_path"]
device = torch.device('cuda' if args['gpu'] == 'gpu' and torch.cuda.is_available() else 'cpu')
print("Device selected  :  ", device)


############################################
#               Functions
############################################

def load_checkpoint(filename, device):
    """
    function that loads a checkpoint of a previously trained model and rebuilds the model

    Args:
        filename: name of the checkpoint file of pre trained model
        device: Executor device
    Returns:
        model: loaded trained model from filename
        output_size: output size of loaded model
    """

    checkpoint = torch.load(filename)

    arch = checkpoint['pretrained_model']
    hidden_units = checkpoint['hidden_units']
    output_size = checkpoint['output_size']
    drop_prob = checkpoint['drop_prob']

    # Construct a model from pretrained network and add a custom classifier
    model, input_size, optimizer = construct_model(arch, hidden_units, output_size, drop_prob)

    model.load_state_dict(checkpoint['model_state_dict'])

    model.class_to_idx = checkpoint['class_to_idx']

    return model, output_size


def predict(image_path, model, device, topk=10):
    """
        Predict the class (or classes) of an image using a trained deep learning model.

        Args:
            image_path: location of the test image
            model: trained model
            device: Executor device
            top k: Top k probability results
        Returns:
            list(top_prob): list of top k probabilities
            top_class: top k classes
    """

    # TODO: Implement the code to predict the class from an image file
    test_image = Image.open(image_path)

    image_ndarray = image_processing_utils.process_image(test_image)

    # turn off dropouts
    model.eval()

    # create a torch tensor of type float32
    image_torch = torch.from_numpy(image_ndarray).type(torch.FloatTensor)

    # Load model / inputs to device  
    model.to(device)
    image_torch = image_torch.to(device)
    print("device :", device)
    print("image_torch :", image_torch.device)

    # reshape to incorporate batch size
    batch_img = torch.unsqueeze(image_torch, 0)

    logps = model(batch_img)
    ps = torch.exp(logps)
    print("Max ps : ", ps.max())
    top_prob, top_idx = ps.topk(topk, dim=1)

    # index to class mapping
    idx_to_class = {value: key for key, value in model.class_to_idx.items()}

    # move tensors to CPU for numpy operations
    top_prob = top_prob.cpu()
    top_idx = top_idx.cpu()

    # convert torch to numpy    
    top_idx = top_idx[0].numpy()
    top_class = [idx_to_class[entry] for entry in top_idx]

    return list(top_prob[0].numpy()), top_class


############################################
#               End of Functions
############################################

# If classification category names file is provided, load it
cat_to_name = []
if category_names_file:
    with open(category_names_file, 'r') as f:
        cat_to_name = json.load(f)

# Re-build the model from the saved checkpoint file
criterion = nn.NLLLoss()
new_model, num_output_classes = load_checkpoint(checkpoint_file, device)
print("Loading checkpoint complete")

# test prediction
with torch.no_grad():
    top_prob, top_class = predict(image_path, new_model, device, top_k)

    image = Image.open(image_path)
    image_ndarray = image_processing_utils.process_image(image)
    image_torch = torch.from_numpy(image_ndarray)
    # image_processing_utils.imshow(image_torch)

    print(top_prob)
    print(top_class)

    # image_processing_utils.view_classify(image_torch, top_prob, top_class, top_k, cat_to_name)

    print("\n\n ** prediction - results **")
    if cat_to_name:
        class_names = [cat_to_name[item] for item in top_class]
    else:
        class_names = top_class
    print("Class name : ", class_names[0])
    print("Class number : ", top_class[0])
    print("Probability : ", top_prob[0], "\n")
