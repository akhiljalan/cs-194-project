import sys
import os
import numpy as np
import tensorflow as tf
slim = tf.contrib.slim

# sys.path.append('discriminator/')
# sys.path.append('image_stylization/')
# sys.path.append('arbitrary_image_stylization_modified/')
# sys.path.append('../')
import arbitrary_image_stylization_build_model as build_model
# import data_processing_utils
# from discriminator.data_processing_utils import load_random_images
import data_utils_all

def discriminator_network(images, reuse_val=tf.AUTO_REUSE, is_training=True): 
	'''
	Simple discriminator network. Reads image batch of size [Batch, 256, 256, 3]
	Outputs labels of size [Batch, 2]
	Representing probability of real/fake 
	'''
	with tf.variable_scope(tf.get_variable_scope(), reuse=reuse_val) and tf.name_scope('discriminator'):
		conv1_out = slim.conv2d(images, 1, [5, 5], activation_fn=tf.nn.relu, scope='discriminator/conv1')
		pool1_out = slim.max_pool2d(conv1_out, [2, 2], stride=2, scope='discriminator/pool1')
		conv2_out = slim.conv2d(pool1_out, 1, [4, 4], stride=2, activation_fn=tf.nn.relu, scope='discriminator/conv2')
		pool2_out = slim.max_pool2d(conv2_out, [6, 6], stride=3, padding='SAME', scope='discriminator/pool2')
		flat_out = slim.flatten(pool2_out, scope='discriminator/flatten3')
		fc1_out = slim.fully_connected(flat_out, 12, scope='discriminator/fc1', activation_fn=tf.nn.relu)
		predictions = slim.fully_connected(fc1_out, 2, scope='discriminator/fc2', activation_fn=tf.nn.softmax)
		pred_argmax = tf.argmax(predictions, axis=1)
		return predictions, pred_argmax

def main():
	# tf.reset_default_graph()
	BATCH_SIZE = 1
	with tf.Graph().as_default():
		# train.MonitoredTraining
		# Loads content images.

		#TODO load test images from a different test path. Do a small amount for simplicity
		# Make sure it's the same content, style images as the test set for the GAN 

		# TODO check the path here. 
		test_content_path = '../testset/content/'
		test_style_path = '../testset/style/'

		# TODO Fix paths? 
		content_path = '/home/noah/magenta/train6/content/'#magenta/data/coco0'
		style_path = '/home/noah/magenta/train6/style/'
		content_inputs_ = data_utils_all.load_random_images(content_path, batch_size=BATCH_SIZE)
		style_inputs_ = data_utils_all.load_random_images(style_path, batch_size=BATCH_SIZE)

		# akhil_dummy_path = '/Users/akhiljalan/Documents/trainingdata_stylized_500/stylized500/'

		# todo insert content_path, style_path... 
		# content_inputs_ = data_utils_all.load_random_images(akhil_dummy_path, batch_size=BATCH_SIZE)
		
		# Loads evaluation style images.
		# style_inputs_ = data_utils_all.load_random_images(akhil_dummy_path, batch_size=BATCH_SIZE)
		
		# Default style, content, and variation weights from magenta. 
		
		content_weights = {"vgg_16/conv3": 1}
		style_weights = {"vgg_16/conv1": 0.5e-3, "vgg_16/conv2": 0.5e-3,
										 "vgg_16/conv3": 0.5e-3, "vgg_16/conv4": 0.5e-3}
		total_variation_weight = 1e4
		
		stylized_images, total_loss_pass_1, loss_dict_pass_1, _ = build_model.build_model(
			content_inputs_,
			style_inputs_,
			reuse=False,
			trainable=True,
			is_training=True,
			inception_end_point='Mixed_6e',
			style_prediction_bottleneck=100,
			adds_losses=True,
			content_weights=content_weights,
			style_weights=style_weights,
			total_variation_weight=total_variation_weight)

		# unstylized_images, total_loss_pass_2, loss_dict_pass_2 = None, 0.0, {}
		
		unstylized_images, total_loss_pass_2, loss_dict_pass_2, _ = build_model.build_model(
			stylized_images, #stylized as content
			content_inputs_, #original content as style
			reuse=tf.AUTO_REUSE,
			trainable=False,
			is_training=False,
			inception_end_point='Mixed_6e',
			style_prediction_bottleneck=100,
			adds_losses=True,
			content_weights=content_weights,
			style_weights=style_weights,
			total_variation_weight=total_variation_weight)
		
		# Log all losses to tensorboard. 
		# loss_dict = {}
		# loss_dict.update(loss_dict_pass_1)
		# loss_dict.update(loss_dict_pass_2)
		tf.summary.scalar("loss1", total_loss_pass_1)
		tf.summary.scalar("loss2", total_loss_pass_2)
		for key, value in loss_dict_pass_1.iteritems():
			tf.summary.scalar(key, value)
		for key, value in loss_dict_pass_2.iteritems():
			tf.summary.scalar(key+"_2", value)

		# Log images to tensorboard 
		tf.summary.image('image/0_content_inputs', content_inputs_, 3)
		# tf.summary.image('image/1_style_inputs_orig', style_inputs_orig_, 3)
		tf.summary.image('image/1_style_inputs', style_inputs_, 3)
		tf.summary.image('image/2_stylized_images', stylized_images, 3)
		tf.summary.image('image/3_unstylized_images', unstylized_images, 3)
			


		real_labels = data_utils_all.gen_labels(is_real=True, batch_size=BATCH_SIZE)
		fake_labels = data_utils_all.gen_labels(is_real=False, batch_size=BATCH_SIZE)

		discrim_inputs = tf.concat([content_inputs_, unstylized_images], axis=0)
		# discrim_labels = tf.concat([real_labels, fake_labels], axis=0)
		discrim_predictions, discrim_pred_classes = discriminator_network(discrim_inputs, reuse_val=False)
		discrim_real_predictions, discrim_fake_predictions = tf.split(discrim_predictions, 2)
		discrim_real_pred_classes, discrim_fake_pred_classes = tf.split(discrim_pred_classes, 2)
		# discrim_real_predictions, discrim_real_pred_classes = discriminator_network(content_inputs_, reuse_val=False)
		# discrim_fake_predictions, discrim_fake_pred_classes= discriminator_network(unstylized_images, reuse_val=tf.AUTO_REUSE)
		
		# Generate label tensors on the fly. 


		discrim_fake_loss = slim.losses.softmax_cross_entropy(discrim_fake_predictions, fake_labels)
		discrim_real_loss = slim.losses.softmax_cross_entropy(discrim_real_predictions, real_labels)
		gen_fooling_loss = slim.losses.softmax_cross_entropy(discrim_fake_predictions, real_labels)
		discrim_fake_acc = slim.metrics.accuracy(discrim_fake_pred_classes, tf.argmax(fake_labels, axis=1))
		discrim_real_acc = slim.metrics.accuracy(discrim_real_pred_classes, tf.argmax(real_labels, axis=1))

		# discrim_fake_loss = slim.losses.softmax_cross_entropy(discrim_predictions, real_labels)

		# gen_fooling_loss = slim.losses.softmax_cross_entropy(discrim_predictions, fake_labels)

		tf.summary.scalar("discrim_real_loss", discrim_real_loss)
		tf.summary.scalar("discrim_foolingg_loss", discrim_fake_loss)
		tf.summary.scalar("gen_fooling_loss", gen_fooling_loss)
		tf.summary.scalar("discrim_total_loss", discrim_real_loss + discrim_fake_loss)		
		tf.summary.scalar("discrim_real_acc", discrim_real_acc)
		tf.summary.scalar("discrim_fake_acc", discrim_fake_acc)
		gen_optimizer = tf.train.AdamOptimizer(learning_rate=1e-2)
		gen_train_op = slim.learning.create_train_op(
			total_loss_pass_1 + 2e5 * gen_fooling_loss, # + total_loss_pass_2? 
			gen_optimizer,
			summarize_gradients=False)

		discr_optimizer = tf.train.AdamOptimizer(learning_rate=1e-2)
		discr_train_op = slim.learning.create_train_op(
			discrim_fake_loss + discrim_real_loss, # + total_loss_pass_2? 
			discr_optimizer,
			summarize_gradients=True)		
		
		# todo merge train ops
		combined_op = tf.group(gen_train_op, discr_train_op)
		# combined_op = gen_train_op


		# Get checkpoint files. 
		# See above for the inception, vgg checkpoints. 
		
		# TODO change checkpoint path...
		gen_checkpoint = '/home/noah/arbitrary_style_transfer/model.ckpt'
		# gen_checkpoint = '../../magenta/arbitrary_style_transfer/model.ckpt'
		# discrim_checkpoint = './logdir/model.ckpt-85'
		
		model_vars = slim.get_model_variables()
		# model_vars = slim.get_variables_to_restore()
		# No saved model yet! 
		# discrim_var_names = [var for var in model_vars if 'discriminator' in var.name]
		# gen_var_names = [var for var in model_vars if 'beta' not in var.name]
		gen_var_names = [var for var in model_vars if 'discriminator' not in var.name]
		# gen_var_names = model_vars #
		# print(gen_var_names)


		# gen_assign_op, gen_feed_dict = slim.assign_from_checkpoint(gen_checkpoint, gen_var_names) #TODO change this...
		# discrim_assign_op, discrim_feed_dict = slim.assign_from_checkpoint(discrim_checkpoint,
		#                                            discrim_var_names)

		init_fn = slim.assign_from_checkpoint_fn(gen_checkpoint, gen_var_names)

		

		def init_assign_func(sess):
			# sess.run(gen_assign_op, gen_feed_dict)
			init_fn(sess)	#			

		
		slim.learning.train(
			train_op=combined_op, #todo replace with merged train op. 
			logdir='./logdir_combinedop3/',
			number_of_steps=7000000,
			save_summaries_secs=1,
			save_interval_secs=1,
			init_fn=init_assign_func)

		# init_fn=init_assign_func,
if __name__ == '__main__':
  main()