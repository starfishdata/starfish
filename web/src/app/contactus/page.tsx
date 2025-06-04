'use client'

import { Button } from "@/components/ui/button"
import { Mail, Calendar, ExternalLink } from 'lucide-react'
import { motion } from "framer-motion"

export default function ContactUs() {
  return (
    <div className="min-h-screen bg-[#FDF2F8] py-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header Section */}
        <motion.section 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Let's Start a <span className="text-pink-600">Conversation</span>
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Have questions? We'd love to hear from you. Let's transform your data challenges into opportunities.
          </p>
        </motion.section>

        {/* Contact Options */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto"
        >
          {/* Email Contact */}
          <div className="bg-white rounded-2xl p-8 shadow-xl hover:shadow-2xl transition-shadow">
            <div className="flex items-center space-x-4 mb-6">
              <div className="bg-pink-100 p-4 rounded-full">
                <Mail className="h-8 w-8 text-pink-600" />
              </div>
              <h2 className="text-2xl font-semibold text-gray-900">Email Us</h2>
            </div>
            <p className="text-gray-600 mb-6">
              Drop us a line anytime! We'll get back to you within 24 hours.
            </p>
            <a 
              href="mailto:founders@starfishdata.ai"
              className="inline-flex items-center text-pink-600 hover:text-pink-700 font-medium"
            >
              founders@starfishdata.ai
              <ExternalLink className="ml-2 h-4 w-4" />
            </a>
          </div>

          {/* Schedule Meeting */}
          <div className="bg-white rounded-2xl p-8 shadow-xl hover:shadow-2xl transition-shadow">
            <div className="flex items-center space-x-4 mb-6">
              <div className="bg-pink-100 p-4 rounded-full">
                <Calendar className="h-8 w-8 text-pink-600" />
              </div>
              <h2 className="text-2xl font-semibold text-gray-900">Book a Meeting</h2>
            </div>
            <p className="text-gray-600 mb-6">
              Schedule a 30-minute call to discuss your needs and see how we can help.
            </p>
            <a 
              href="https://calendly.com/d/crsb-ckq-fv2/chat-with-starfishdata-team"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center w-full bg-pink-600 hover:bg-pink-700 text-white py-3 px-6 rounded-lg transition-colors"
            >
              <Calendar className="h-5 w-5 mr-2" />
              Schedule Time
            </a>
          </div>
        </motion.div>

        {/* Additional Info */}
        <motion.section 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-16 text-center"
        >
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">
            What Happens Next?
          </h2>
          <div className="grid md:grid-cols-3 gap-8 max-w-3xl mx-auto mt-8">
            <div>
              <div className="text-pink-600 font-bold text-xl mb-2">1</div>
              <h3 className="font-medium text-gray-900 mb-2">Initial Contact</h3>
              <p className="text-gray-600">We'll respond to your inquiry within 24 hours</p>
            </div>
            <div>
              <div className="text-pink-600 font-bold text-xl mb-2">2</div>
              <h3 className="font-medium text-gray-900 mb-2">Discovery Call</h3>
              <p className="text-gray-600">We'll discuss your needs and how we can help</p>
            </div>
            <div>
              <div className="text-pink-600 font-bold text-xl mb-2">3</div>
              <h3 className="font-medium text-gray-900 mb-2">Solution Planning</h3>
              <p className="text-gray-600">We'll create a tailored plan for your success</p>
            </div>
          </div>
        </motion.section>
      </div>
    </div>
  )
}